"""Sens des dépendances (AD-1), vérifié par analyse `ast` des imports de `src/waveaudit/`."""

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src"
PAQUET = SRC / "waveaudit"

# Bibliothèque tierce -> préfixes de modules (relatifs à waveaudit/) autorisés à l'importer.
RESERVES: dict[str, tuple[str, ...]] = {
    "cvss": ("domaine/cvss31.py",),
    "httpx": ("adaptateurs/", "installation/telechargement.py"),
    "psutil": ("adaptateurs/",),
    "yaml": ("adaptateurs/",),
    "docx": ("adaptateurs/",),
    "fastapi": ("interfaces/web/",),
    "starlette": ("interfaces/web/",),
    "jinja2": ("interfaces/web/",),
    "multipart": ("interfaces/web/",),
    "python_multipart": ("interfaces/web/",),
    "uvicorn": ("interfaces/cli.py",),
    "typer": ("interfaces/cli.py",),
}


@dataclass(frozen=True)
class Import:
    module: str  # nom absolu importé
    ligne: int
    niveau_module: bool  # False si l'import est dans une fonction


def _nom_module(fichier: Path) -> str:
    parties = list(fichier.relative_to(SRC).with_suffix("").parts)
    if parties[-1] == "__init__":
        parties.pop()
    return ".".join(parties)


def _imports(fichier: Path) -> list[Import]:
    arbre = ast.parse(fichier.read_text(encoding="utf-8"), filename=str(fichier))
    paquet = _nom_module(fichier).split(".")
    if fichier.name != "__init__.py":
        paquet = paquet[:-1]
    resultat: list[Import] = []

    def visiter(noeud: ast.AST, dans_fonction: bool) -> None:
        for enfant in ast.iter_child_nodes(noeud):
            fonction = dans_fonction or isinstance(
                enfant, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda
            )
            if isinstance(enfant, ast.Import):
                for alias in enfant.names:
                    resultat.append(Import(alias.name, enfant.lineno, not dans_fonction))
            elif isinstance(enfant, ast.ImportFrom):
                if enfant.level:
                    base = paquet[: len(paquet) - enfant.level + 1]
                    nom = ".".join(base + ([enfant.module] if enfant.module else []))
                else:
                    nom = enfant.module or ""
                resultat.append(Import(nom, enfant.lineno, not dans_fonction))
                # `from waveaudit import adaptateurs` : le nom importé peut être un module.
                for alias in enfant.names:
                    resultat.append(Import(f"{nom}.{alias.name}", enfant.lineno, not dans_fonction))
            visiter(enfant, fonction)

    visiter(arbre, False)
    return resultat


FICHIERS = sorted(PAQUET.rglob("*.py"))
TOUS = [(f.relative_to(PAQUET).as_posix(), imp) for f in FICHIERS for imp in _imports(f)]


def _sous(chemin: str, prefixes: tuple[str, ...]) -> bool:
    return any(chemin == p or (p.endswith("/") and chemin.startswith(p)) for p in prefixes)


def _racine(module: str) -> str:
    return module.split(".")[0]


def _waveaudit(module: str, sous_paquet: str) -> bool:
    return module == f"waveaudit.{sous_paquet}" or module.startswith(f"waveaudit.{sous_paquet}.")


def test_fichiers_trouves():
    assert len(FICHIERS) > 10
    assert any(chemin == "domaine/modeles.py" for chemin, _ in TOUS)


@pytest.mark.parametrize("couche", ["domaine", "workflows"])
def test_noyau_stdlib_pydantic_domaine(couche):
    autorises_internes = ("domaine",) if couche == "domaine" else ("domaine", "workflows")
    fautes = []
    for chemin, imp in TOUS:
        if not chemin.startswith(f"{couche}/"):
            continue
        racine = _racine(imp.module)
        if racine in sys.stdlib_module_names or racine == "pydantic":
            continue
        if racine == "waveaudit" and any(_waveaudit(imp.module, c) for c in autorises_internes):
            continue
        if racine == "cvss" and chemin == "domaine/cvss31.py":
            continue
        fautes.append(f"{chemin}:{imp.ligne} importe {imp.module}")
    assert fautes == []


def test_bibliotheques_reservees():
    fautes = [
        f"{chemin}:{imp.ligne} importe {imp.module}"
        for chemin, imp in TOUS
        if _racine(imp.module) in RESERVES and not _sous(chemin, RESERVES[_racine(imp.module)])
    ]
    assert fautes == []


def test_installation_importee_par_application_et_cli():
    fautes = [
        f"{chemin}:{imp.ligne} importe {imp.module}"
        for chemin, imp in TOUS
        if _waveaudit(imp.module, "installation")
        and not _sous(chemin, ("installation/", "application/", "interfaces/cli.py"))
    ]
    assert fautes == []


def test_adaptateurs_instancies_par_la_composition_seule():
    """Seule `application/composition.py` importe les adaptateurs au niveau module.

    `interfaces/cli.py` peut importer un adaptateur dans une fonction (ex. `catalogue
    verifier`), jamais au niveau module (contrats §12).
    """
    fautes = []
    for chemin, imp in TOUS:
        if not _waveaudit(imp.module, "adaptateurs"):
            continue
        if _sous(chemin, ("adaptateurs/", "application/composition.py")):
            continue
        if chemin == "interfaces/cli.py" and not imp.niveau_module:
            continue
        fautes.append(f"{chemin}:{imp.ligne} importe {imp.module}")
    assert fautes == []


def test_adaptateurs_sans_couche_superieure():
    """Les adaptateurs ne dépendent que du domaine : ni application, ni interfaces, ni workflows."""
    fautes = [
        f"{chemin}:{imp.ligne} importe {imp.module}"
        for chemin, imp in TOUS
        if chemin.startswith("adaptateurs/")
        and any(_waveaudit(imp.module, c) for c in ("application", "interfaces", "workflows"))
    ]
    assert fautes == []


MODULE_LOT = "waveaudit.application.lot"
TESTS = Path(__file__).resolve().parents[1]


def _noms_prives_de_lot(source: str, nom_fichier: str, paquet: list[str]) -> list[str]:
    """Noms `_…` de `waveaudit.application.lot` importés ou lus (`lot._x`) dans `source`."""
    arbre = ast.parse(source, filename=nom_fichier)
    alias_module: set[str] = set()
    fautes: list[str] = []
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.ImportFrom):
            if noeud.level:
                base = paquet[: len(paquet) - noeud.level + 1]
                module = ".".join(base + ([noeud.module] if noeud.module else []))
            else:
                module = noeud.module or ""
            for alias in noeud.names:
                if module == MODULE_LOT and alias.name.startswith("_"):
                    fautes.append(f"{nom_fichier}:{noeud.lineno} importe {alias.name}")
                if f"{module}.{alias.name}" == MODULE_LOT:
                    alias_module.add(alias.asname or alias.name)
        elif isinstance(noeud, ast.Import):
            for alias in noeud.names:
                if alias.name == MODULE_LOT and alias.asname:
                    alias_module.add(alias.asname)
    for noeud in ast.walk(arbre):
        if (
            isinstance(noeud, ast.Attribute)
            and noeud.attr.startswith("_")
            and not noeud.attr.startswith("__")
            and (
                (isinstance(noeud.value, ast.Name) and noeud.value.id in alias_module)
                or ast.unparse(noeud.value) == MODULE_LOT  # import sans alias, nom qualifié
            )
        ):
            fautes.append(f"{nom_fichier}:{noeud.lineno} lit {ast.unparse(noeud)}")
    return fautes


def test_noms_prives_de_lot_non_importes_hors_de_lot():
    """CAP-16 (§9 v2) : hors de `application/lot.py`, aucun nom `_…` de `lot.py`, tests compris."""
    fautes = []
    for fichier in FICHIERS:
        if fichier.relative_to(PAQUET).as_posix() == "application/lot.py":
            continue
        paquet = _nom_module(fichier).split(".")
        if fichier.name != "__init__.py":
            paquet = paquet[:-1]
        source = fichier.read_text(encoding="utf-8")
        fautes += _noms_prives_de_lot(source, fichier.name, paquet)
    for fichier in sorted(TESTS.rglob("*.py")):
        source = fichier.read_text(encoding="utf-8")
        fautes += _noms_prives_de_lot(source, fichier.name, ["tests"])
    assert fautes == []


@pytest.mark.parametrize(
    "source",
    [
        "from waveaudit.application.lot import _ID_LOT\n",
        "from waveaudit.application import lot\nlot._sans_chemin('x')\n",
        "import waveaudit.application.lot as l\nl._Emetteur\n",
        "from waveaudit.application import lot as module_lot\nmodule_lot._sorties\n",
        "import waveaudit.application.lot\nwaveaudit.application.lot._sans_chemin('x')\n",
    ],
)
def test_noms_prives_de_lot_detectes(source):
    """Contrôle de l'analyseur de la règle précédente."""
    assert _noms_prives_de_lot(source, "exemple.py", ["tests"]) != []


def test_noms_publics_de_lot_admis():
    source = (
        "from waveaudit.application.lot import MOTIF_ID_LOT, Emetteur, sans_chemin\n"
        "from waveaudit.application import lot\nlot.dossier_sorties\nlot.__name__\n"
    )
    assert _noms_prives_de_lot(source, "exemple.py", ["tests"]) == []


def test_analyse_detecte_les_imports():
    """Contrôle de l'analyseur lui-même : imports relatifs, `from x import y`, fonctions."""
    fichier = PAQUET / "workflows" / "registre.py"
    modules = {imp.module: imp.niveau_module for imp in _imports(fichier)}
    assert modules["waveaudit.domaine.ports"] is True
    assert modules["waveaudit.workflows.fiches"] is False
