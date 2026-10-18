"""CLI de bout en bout (contrats §4, §12, §19), `typer.testing.CliRunner`, faux moteur.

Chaque test de `fiches` écrit sa propre configuration TOML sous `tmp_path` et la passe par
`--config` ; aucun test n'écrit dans le `var/` du dépôt (AD-10).
"""

import json
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from docx import Document
from typer.testing import CliRunner

from waveaudit.adaptateurs.export_docx import LIBELLES
from waveaudit.application.config import racine_projet
from waveaudit.interfaces.cli import app
from waveaudit.securite import garde_reseau

DEMO = racine_projet() / "donnees" / "demo" / "notes"
BANDEAU = "Démonstration — données fictives"
runner = CliRunner()


def _toml(sections: dict[str, dict[str, Any]]) -> str:
    """Sérialise un petit sous-ensemble de TOML (sections à plat, assez pour ces tests)."""
    blocs = []
    for nom, valeurs in sections.items():
        lignes = [f"[{nom}]"]
        for cle, valeur in valeurs.items():
            if isinstance(valeur, bool):
                lignes.append(f"{cle} = {'true' if valeur else 'false'}")
            elif isinstance(valeur, str):
                lignes.append(f'{cle} = "{valeur}"')
            elif isinstance(valeur, Iterable) and not isinstance(valeur, (int, float)):
                items = ", ".join(f'"{v}"' for v in valeur)
                lignes.append(f"{cle} = [{items}]")
            else:
                lignes.append(f"{cle} = {valeur}")
        blocs.append("\n".join(lignes))
    return "\n\n".join(blocs)


def _ecrire_config(
    tmp_path: Path,
    *,
    mode: str = "externe",
    base_url: str = "",
    catalogue: Path | None = None,
) -> Path:
    chemins = {
        "var": (tmp_path / "var").as_posix(),
        "theme_prive": (tmp_path / "theme-prive").as_posix(),
    }
    if catalogue is not None:
        chemins["catalogue"] = catalogue.as_posix()
    texte = _toml(
        {
            "moteur": {"mode": mode, "base_url": base_url, "timeout_s": 1.0},
            "chemins": chemins,
        }
    )
    chemin = tmp_path / "waveaudit-test.toml"
    chemin.write_text(texte, encoding="utf-8")
    return chemin


def test_fiches_nominal_30_notes_bandeau_et_garde(tmp_path, faux_moteur):
    config = _ecrire_config(tmp_path, base_url=faux_moteur().base_url)
    resultat = runner.invoke(app, ["fiches", str(DEMO), "--config", str(config)])

    assert resultat.exit_code == 0, resultat.output
    lignes = resultat.output.splitlines()
    assert lignes[0] == BANDEAU
    assert lignes[-1] == BANDEAU
    lignes_fiche = [ligne for ligne in lignes if ligne.startswith("[")]
    assert len(lignes_fiche) == 30
    assert any("rapport :" in ligne for ligne in lignes)
    assert not garde_reseau._actif  # désactivé en sortie de commande


def test_fiches_langue_en_rapport_anglais(tmp_path, faux_moteur):
    """[v2] CAP-8 (contrats §19, §23) : `--langue en` -> rapport Word aux libellés anglais."""
    config = _ecrire_config(tmp_path, base_url=faux_moteur().base_url)
    dossier = tmp_path / "notes"
    dossier.mkdir()
    (dossier / "01-xss-reflechi.md").write_bytes((DEMO / "01-xss-reflechi.md").read_bytes())

    resultat = runner.invoke(
        app, ["fiches", str(dossier), "--config", str(config), "--langue", "en"]
    )

    assert resultat.exit_code == 0, resultat.output
    ligne_rapport = next(ligne for ligne in resultat.output.splitlines() if "rapport :" in ligne)
    chemin_rapport = Path(ligne_rapport.rsplit("rapport :", 1)[1].strip())
    document = Document(str(chemin_rapport))
    titres = [p.text for p in document.paragraphs if p.style.name == "Title"]
    assert LIBELLES["en"]["titre"] in titres


def test_fiches_langue_invalide_code_2(tmp_path, faux_moteur):
    config = _ecrire_config(tmp_path, base_url=faux_moteur().base_url)
    resultat = runner.invoke(app, ["fiches", str(DEMO), "--config", str(config), "--langue", "de"])

    assert resultat.exit_code == 2


def test_fiches_dossier_absent_code_2(tmp_path, faux_moteur):
    config = _ecrire_config(tmp_path, base_url=faux_moteur().base_url)
    resultat = runner.invoke(app, ["fiches", str(tmp_path / "absent"), "--config", str(config)])

    assert resultat.exit_code == 2
    assert resultat.output.strip()
    assert str(tmp_path) not in resultat.output  # AD-8, message passé par `lot.sans_chemin`
    assert not garde_reseau._actif


def test_fiches_moteur_injoignable_code_3(tmp_path, faux_moteur):
    config = _ecrire_config(tmp_path, base_url=faux_moteur("injoignable").base_url)
    resultat = runner.invoke(app, ["fiches", str(DEMO), "--config", str(config)])

    assert resultat.exit_code == 3


def test_fiches_modele_inconnu_local_gere_code_2(tmp_path):
    config = _ecrire_config(tmp_path, mode="local-gere")
    resultat = runner.invoke(
        app, ["fiches", str(DEMO), "--config", str(config), "--modele", "inconnu-xyz"]
    )

    assert resultat.exit_code == 2


def test_fiches_sortie_verrouillee_code_4(tmp_path, faux_moteur):
    config = _ecrire_config(tmp_path, base_url=faux_moteur().base_url)
    verrou = tmp_path / "verrou"
    verrou.mkdir()  # copyfile vers un dossier existant lève PermissionError sous Windows
    resultat = runner.invoke(app, ["fiches", str(DEMO), "--config", str(config), "-o", str(verrou)])

    assert resultat.exit_code == 4
    assert "accès refusé" in resultat.output
    assert str(tmp_path) not in resultat.output


def test_catalogue_verifier_depot_valide_code_0():
    resultat = runner.invoke(app, ["catalogue", "verifier"])

    assert resultat.exit_code == 0


def test_catalogue_verifier_casse_code_2(tmp_path):
    catalogue = tmp_path / "catalogue"
    catalogue.mkdir()
    (catalogue / "web.yaml").write_text("pas_une_liste: true\n", encoding="utf-8")
    config = _ecrire_config(tmp_path, catalogue=catalogue)
    resultat = runner.invoke(app, ["catalogue", "verifier", "--config", str(config)])

    assert resultat.exit_code == 2
    assert resultat.output.strip()


def test_ui_lance_uvicorn_avec_la_vraie_creer_app(monkeypatch, tmp_path):
    """Vraie `interfaces.web.app.creer_app` ; seul `uvicorn.run` est remplacé. Le port de
    `--port` doit atteindre le middleware Host de l'application créée."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    config = _ecrire_config(tmp_path)
    appels: dict[str, Any] = {}

    def faux_run(application: Any, *, host: str, port: int) -> None:
        appels["run"] = (application, host, port)
        appels["garde_actif"] = garde_reseau._actif

    monkeypatch.setattr("uvicorn.run", faux_run)

    resultat = runner.invoke(app, ["ui", "--config", str(config), "--port", "9999"])

    assert resultat.exit_code == 0, resultat.output
    application, hote, port = appels["run"]
    assert isinstance(application, FastAPI)
    assert (hote, port) == ("127.0.0.1", 9999)
    assert appels["garde_actif"]  # uvicorn démarre sous le garde
    assert not garde_reseau._actif
    client = TestClient(application)
    assert client.get("/", headers={"host": "127.0.0.1:9999"}).status_code == 200
    assert client.get("/", headers={"host": "127.0.0.1:8765"}).status_code == 400


def test_ui_port_hors_bornes_code_2(tmp_path):
    resultat = runner.invoke(
        app, ["ui", "--config", str(_ecrire_config(tmp_path)), "--port", "70000"]
    )

    assert resultat.exit_code == 2


def test_ui_port_occupe_code_4(monkeypatch, tmp_path):
    def faux_run(application: Any, *, host: str, port: int) -> None:
        sys.exit(1)  # comportement d'uvicorn quand le bind échoue

    monkeypatch.setattr("uvicorn.run", faux_run)
    resultat = runner.invoke(app, ["ui", "--config", str(_ecrire_config(tmp_path))])

    assert resultat.exit_code == 4
    assert "port" in resultat.output
    assert not garde_reseau._actif


def test_ui_hote_invalide_code_2(tmp_path):
    chemin = tmp_path / "waveaudit-test.toml"
    chemin.write_text('[ui]\nhote = "0.0.0.0"\n', encoding="utf-8")
    resultat = runner.invoke(app, ["ui", "--config", str(chemin)])

    assert resultat.exit_code == 2
    assert not garde_reseau._actif


def test_banc_dossier_absent_code_2(tmp_path):
    """Branchement réel de `banc` sur `application.banc.executer_banc` (story 15) : l'erreur de
    dossier manquant est levée avant tout accès au moteur, donc sans configuration dédiée."""
    resultat = runner.invoke(app, ["banc", str(tmp_path / "absent")])

    assert resultat.exit_code == 2
    assert not garde_reseau._actif


def test_banc_succes_code_0(monkeypatch, config_test):
    """Chemin nominal de `banc` par la CLI : faux moteur (config_test), mesure mémoire factice."""
    import os

    from waveaudit.application import composition
    from waveaudit.interfaces import cli

    class _Mesure:
        def rss_octets(self, pid: int) -> int | None:
            return 1000 if pid == os.getpid() else None

    monkeypatch.setattr(cli, "_charger_config", lambda chemin=None: config_test)
    monkeypatch.setattr(composition, "creer_mesure_memoire", _Mesure)

    resultat = runner.invoke(app, ["banc", str(DEMO)])

    assert resultat.exit_code == 0, resultat.output
    (chemin,) = (config_test.chemins.var / "sorties").glob("*/banc.json")
    donnees = json.loads(chemin.read_text(encoding="utf-8"))
    assert donnees["pic_rss_app_o"] == 1000
    assert len(donnees["fiches"]) == len([*DEMO.glob("*.md"), *DEMO.glob("*.txt")])
    assert "top1" in resultat.output
    assert not garde_reseau._actif


def test_banc_seed_cli(monkeypatch, config_test):
    """[revue B1] `banc --seed 142` atteint banc.json ; seed hors de 0..2**32-1 -> code 2."""
    from waveaudit.application import composition
    from waveaudit.interfaces import cli

    class _Mesure:
        def rss_octets(self, pid: int) -> int | None:
            return None

    monkeypatch.setattr(cli, "_charger_config", lambda chemin=None: config_test)
    monkeypatch.setattr(composition, "creer_mesure_memoire", _Mesure)
    notes = config_test.chemins.var.parent / "notes-seed"
    notes.mkdir()
    (notes / "01-xss-reflechi.md").write_bytes((DEMO / "01-xss-reflechi.md").read_bytes())

    resultat = runner.invoke(app, ["banc", str(notes), "--seed", "142"])

    assert resultat.exit_code == 0, resultat.output
    (chemin,) = (config_test.chemins.var / "sorties").glob("*/banc.json")
    assert json.loads(chemin.read_text(encoding="utf-8"))["seed"] == 142
    assert "ok 1/1" in resultat.output
    for hors_borne in ("-1", str(2**32)):
        assert runner.invoke(app, ["banc", str(notes), "--seed", hors_borne]).exit_code == 2


def test_banc_erreurs_traduites_en_codes(monkeypatch, tmp_path):
    from waveaudit.domaine.erreurs import EntreeInvalide, MoteurInjoignable

    faux_banc = type(sys)("waveaudit.application.banc")
    monkeypatch.setitem(sys.modules, "waveaudit.application.banc", faux_banc)
    for erreur, code in ((EntreeInvalide("x"), 2), (MoteurInjoignable("x"), 3), (KeyError(1), 4)):

        def leve(*a: Any, erreur: Exception = erreur) -> None:
            raise erreur

        faux_banc.executer_banc = leve
        resultat = runner.invoke(app, ["banc", str(tmp_path)])
        assert resultat.exit_code == code, (erreur, resultat.output)
    assert not garde_reseau._actif


def test_fiches_modele_externe_surcharge_modele_api(tmp_path, faux_moteur):
    config = _ecrire_config(tmp_path, base_url=faux_moteur().base_url)
    resultat = runner.invoke(
        app, ["fiches", str(DEMO), "--config", str(config), "--modele", "mon-modele"]
    )

    assert resultat.exit_code == 0, resultat.output
    (journal,) = (tmp_path / "var" / "sorties").glob("*/journal.jsonl")
    demarre = json.loads(journal.read_text(encoding="utf-8").splitlines()[0])
    assert demarre["type"] == "lot_demarre"
    assert demarre["details"]["modele"] == "mon-modele"


def test_sbom_succes_code_0(monkeypatch):
    monkeypatch.setattr(
        "waveaudit.installation.sbom.generer", lambda var: Path(var) / "sbom.cdx.json"
    )
    resultat = runner.invoke(app, ["sbom"])

    assert resultat.exit_code == 0
    assert "sbom" in resultat.output.lower()


def test_sbom_echec_disque_code_4(monkeypatch):
    def leve(var: Path) -> Path:
        raise OSError("disque plein")

    monkeypatch.setattr("waveaudit.installation.sbom.generer", leve)
    resultat = runner.invoke(app, ["sbom"])

    assert resultat.exit_code == 4


def test_installer_succes_code_0(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "waveaudit.installation.telechargement.installer", lambda *a, **k: [tmp_path / "x"]
    )
    resultat = runner.invoke(app, ["installer"])

    assert resultat.exit_code == 0


def test_installer_empreinte_invalide_code_5(monkeypatch):
    from waveaudit.domaine.erreurs import EmpreinteInvalide

    def leve(*a: Any, **k: Any) -> None:
        raise EmpreinteInvalide("empreinte invalide")

    monkeypatch.setattr("waveaudit.installation.telechargement.installer", leve)
    resultat = runner.invoke(app, ["installer"])

    assert resultat.exit_code == 5


def test_installer_erreur_httpx_code_4(monkeypatch):
    import httpx

    def leve(*a: Any, **k: Any) -> None:
        raise httpx.ConnectError("hors ligne")

    monkeypatch.setattr("waveaudit.installation.telechargement.installer", leve)
    resultat = runner.invoke(app, ["installer"])

    assert resultat.exit_code == 4


def test_installer_manifeste_invalide_code_2(monkeypatch):
    from waveaudit.domaine.erreurs import ConfigurationInvalide

    def leve(*a: Any, **k: Any) -> None:
        raise ConfigurationInvalide("manifeste invalide")

    monkeypatch.setattr("waveaudit.installation.manifeste.charger", leve)
    resultat = runner.invoke(app, ["installer"])

    assert resultat.exit_code == 2
    assert "manifeste invalide" in resultat.output


def test_installer_erreur_os_code_4(monkeypatch):
    def leve(*a: Any, **k: Any) -> None:
        raise OSError("disque plein")

    monkeypatch.setattr("waveaudit.installation.telechargement.installer", leve)
    resultat = runner.invoke(app, ["installer"])

    assert resultat.exit_code == 4


# --- exporter (contrats §27, CAP-13, CAP-17) ---------------------------------------------------


def _lot_a_exporter(
    config_chemin: Path, id_lot: str, *, valide: bool = True, notes_non_validees: int = 0
) -> Path:
    """Lot `fiches` : une entrée (validée ou non), plus `notes_non_validees` jamais validées."""
    from waveaudit.application import relecture as relecture_app
    from waveaudit.application.config import charger_configuration
    from waveaudit.application.lot import dossier_sorties, ecrire_fiche_lot
    from waveaudit.domaine.modeles import (
        Candidat,
        Cvss,
        Fiche,
        Note,
        Reference,
        Statut,
        Tracabilite,
    )
    from waveaudit.domaine.relecture import valider

    cfg = charger_configuration(config_chemin)
    dossier = dossier_sorties(cfg) / id_lot
    dossier.mkdir(parents=True, exist_ok=True)
    ecrire_fiche_lot(dossier, id_lot=id_lot, workflow="fiches", langue="fr", modele_demande=None)
    noms = ["01-sqli.md"] + [f"0{2 + i}-autre.md" for i in range(notes_non_validees)]
    notes = [
        Note(
            fichier=nom,
            titre="Injection",
            actif=None,
            severite_pressentie=None,
            constat_attendu="WEB-001",
            corps="Paramètre id injectable.",
        )
        for nom in noms
    ]
    relecture_app.initialiser(
        dossier, id_lot=id_lot, langue="fr", modele="externe", modele_demande=None, elements=notes
    )
    cvss = Cvss(
        vecteur="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H", score=9.8, severite="critique"
    )
    ref = Reference(id="CWE-89", titre="Injection SQL", url="https://cwe.mitre.org/data/89")

    def _fiche(nom: str) -> Fiche:
        return Fiche(
            titre="Injection SQL",
            description="d" * 30,
            impact="i" * 30,
            recommandation="r" * 30,
            cvss=cvss,
            references=[ref],
            statut=Statut.OK,
            motifs=[],
            tracabilite=Tracabilite(
                note=nom,
                constat_id="WEB-001",
                candidats=[Candidat(id="WEB-001", score=3.2)],
                constat_attendu=None,
            ),
        )

    for index, nom in enumerate(noms, start=1):
        relecture_app.enregistrer_resultat(dossier, index, _fiche(nom))
    if valide:
        relecture_app.modifier(dossier, 1, 2, valider)
    return dossier


def test_exporter_final_code_0_bandeau_et_fiches_non_validees(tmp_path, faux_moteur):
    config = _ecrire_config(tmp_path, base_url=faux_moteur().base_url)
    _lot_a_exporter(config, "lot-final", valide=False)

    resultat = runner.invoke(app, ["exporter", "lot-final", "--config", str(config)])

    assert resultat.exit_code == 2  # aucune fiche validée
    assert not garde_reseau._actif


def test_exporter_final_avec_fiche_validee_code_0(tmp_path, faux_moteur):
    config = _ecrire_config(tmp_path, base_url=faux_moteur().base_url)
    dossier = _lot_a_exporter(config, "lot-final-ok", valide=True)

    resultat = runner.invoke(app, ["exporter", "lot-final-ok", "--config", str(config)])

    assert resultat.exit_code == 0, resultat.output
    lignes = resultat.output.splitlines()
    assert lignes[0] == BANDEAU
    assert lignes[-1] == BANDEAU
    assert any("rapport :" in ligne for ligne in lignes)
    assert (dossier / "rapport-lot-final-ok.docx").is_file()
    assert not garde_reseau._actif


def test_exporter_brouillon_sans_ligne_fiches_non_validees(tmp_path, faux_moteur):
    """[revue A17] La ligne « fiches non validées » n'existe qu'en mode final (contrats §27)."""
    config = _ecrire_config(tmp_path, base_url=faux_moteur().base_url)
    _lot_a_exporter(config, "lot-brouillon", valide=False)

    resultat = runner.invoke(
        app, ["exporter", "lot-brouillon", "--brouillon", "--config", str(config)]
    )

    assert resultat.exit_code == 0, resultat.output
    assert "fiches non validées" not in resultat.output
    assert any("rapport :" in ligne for ligne in resultat.output.splitlines())


def test_exporter_final_annonce_les_fiches_non_validees(tmp_path, faux_moteur):
    config = _ecrire_config(tmp_path, base_url=faux_moteur().base_url)
    _lot_a_exporter(config, "lot-final-mixte", valide=True, notes_non_validees=1)

    resultat = runner.invoke(app, ["exporter", "lot-final-mixte", "--config", str(config)])

    assert resultat.exit_code == 0, resultat.output
    assert "fiches non validées : 1 (exclues, listées en annexe)" in resultat.output


def test_exporter_lot_inconnu_code_2(tmp_path, faux_moteur):
    config = _ecrire_config(tmp_path, base_url=faux_moteur().base_url)

    resultat = runner.invoke(app, ["exporter", "jamais-cree", "--config", str(config)])

    assert resultat.exit_code == 2


def test_exporter_lot_incident_code_2(tmp_path, faux_moteur):
    from waveaudit.application.config import charger_configuration
    from waveaudit.application.lot import dossier_sorties, ecrire_fiche_lot

    config = _ecrire_config(tmp_path, base_url=faux_moteur().base_url)
    cfg = charger_configuration(config)
    dossier = dossier_sorties(cfg) / "incident-1"
    dossier.mkdir(parents=True, exist_ok=True)
    ecrire_fiche_lot(
        dossier, id_lot="incident-1", workflow="incident", langue=None, modele_demande=None
    )

    resultat = runner.invoke(app, ["exporter", "incident-1", "--config", str(config)])

    assert resultat.exit_code == 2


def test_exporter_lot_en_cours_code_2(tmp_path, faux_moteur, monkeypatch):
    from waveaudit.application import composition

    config = _ecrire_config(tmp_path, base_url=faux_moteur().base_url)
    dossier = _lot_a_exporter(config, "lot-en-cours", valide=True)
    # pid d'un autre processus (jamais `os.getpid()` du test), simulé vivant (§30).
    chemin_lot_json = dossier / "lot.json"
    contenu = json.loads(chemin_lot_json.read_text(encoding="utf-8"))
    chemin_lot_json.write_text(
        json.dumps(contenu | {"pid": 999_999_999}, ensure_ascii=False), encoding="utf-8"
    )
    monkeypatch.setattr(composition, "processus_actif", lambda pid, cree_le: True)

    resultat = runner.invoke(app, ["exporter", "lot-en-cours", "--config", str(config)])

    assert resultat.exit_code == 2


def test_exporter_fichier_cible_verrouille_code_4(tmp_path, faux_moteur):
    config = _ecrire_config(tmp_path, base_url=faux_moteur().base_url)
    dossier = _lot_a_exporter(config, "lot-verrou", valide=True)
    # Un dossier à la place du fichier cible : `os.replace` lève `PermissionError` sous Windows,
    # comme un document ouvert dans Word.
    (dossier / "rapport-lot-verrou.docx").mkdir()

    resultat = runner.invoke(app, ["exporter", "lot-verrou", "--config", str(config)])

    assert resultat.exit_code == 4
    assert "accès refusé" in resultat.output
    assert str(tmp_path) not in resultat.output


def test_exporter_aucune_commande_ne_valide_une_fiche(tmp_path, faux_moteur):
    from waveaudit.application import relecture as relecture_app
    from waveaudit.application.config import charger_configuration
    from waveaudit.application.lot import dossier_sorties

    config = _ecrire_config(tmp_path, base_url=faux_moteur().base_url)
    dossier = _lot_a_exporter(config, "lot-sans-validation-cli", valide=False)

    runner.invoke(
        app, ["exporter", "lot-sans-validation-cli", "--brouillon", "--config", str(config)]
    )

    cfg = charger_configuration(config)
    assert dossier == dossier_sorties(cfg) / "lot-sans-validation-cli"
    entree = relecture_app.charger(dossier).entrees[0]
    assert entree.statut_relecture == "a_valider"
