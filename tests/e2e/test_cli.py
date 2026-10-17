"""CLI de bout en bout (contrats §4, §12, §19), `typer.testing.CliRunner`, faux moteur.

Chaque test de `fiches` écrit sa propre configuration TOML sous `tmp_path` et la passe par
`--config` ; aucun test n'écrit dans le `var/` du dépôt (AD-10).
"""

import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

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


def test_fiches_nominal_20_notes_bandeau_et_garde(tmp_path, faux_moteur):
    config = _ecrire_config(tmp_path, base_url=faux_moteur().base_url)
    resultat = runner.invoke(app, ["fiches", str(DEMO), "--config", str(config)])

    assert resultat.exit_code == 0, resultat.output
    lignes = resultat.output.splitlines()
    assert lignes[0] == BANDEAU
    assert lignes[-1] == BANDEAU
    lignes_fiche = [ligne for ligne in lignes if ligne.startswith("[")]
    assert len(lignes_fiche) == 20
    assert any("rapport :" in ligne for ligne in lignes)
    assert not garde_reseau._actif  # désactivé en sortie de commande


def test_fiches_dossier_absent_code_2(tmp_path, faux_moteur):
    config = _ecrire_config(tmp_path, base_url=faux_moteur().base_url)
    resultat = runner.invoke(app, ["fiches", str(tmp_path / "absent"), "--config", str(config)])

    assert resultat.exit_code == 2
    assert resultat.output.strip()
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


def test_ui_lance_uvicorn_avec_creer_app(monkeypatch, tmp_path):
    """`interfaces.web.app` (story 14) n'est pas encore sur `main` : import et `uvicorn.run`
    monkeypatchés ici ; l'intégration réelle se vérifie après fusion des deux stories."""
    config = _ecrire_config(tmp_path)
    appels: dict[str, Any] = {}

    def fausse_creer_app(cfg: Any) -> str:
        appels["config"] = cfg
        return "app-web"

    faux_module = type(sys)("waveaudit.interfaces.web.app")
    faux_module.creer_app = fausse_creer_app
    monkeypatch.setitem(sys.modules, "waveaudit.interfaces.web.app", faux_module)

    def faux_run(application: Any, *, host: str, port: int) -> None:
        appels["run"] = (application, host, port)

    monkeypatch.setattr("uvicorn.run", faux_run)

    resultat = runner.invoke(app, ["ui", "--config", str(config), "--port", "9999"])

    assert resultat.exit_code == 0, resultat.output
    assert appels["run"] == ("app-web", "127.0.0.1", 9999)
    assert not garde_reseau._actif


def test_ui_hote_invalide_code_2(tmp_path):
    chemin = tmp_path / "waveaudit-test.toml"
    chemin.write_text('[ui]\nhote = "0.0.0.0"\n', encoding="utf-8")
    resultat = runner.invoke(app, ["ui", "--config", str(chemin)])

    assert resultat.exit_code == 2
    assert not garde_reseau._actif


def test_banc_module_absent_code_2(tmp_path):
    notes = tmp_path / "notes"
    notes.mkdir()
    resultat = runner.invoke(app, ["banc", str(notes)])

    assert resultat.exit_code == 2
    assert "story 15" in resultat.output
    assert not garde_reseau._actif


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


def test_installer_erreur_os_code_4(monkeypatch):
    def leve(*a: Any, **k: Any) -> None:
        raise OSError("disque plein")

    monkeypatch.setattr("waveaudit.installation.telechargement.installer", leve)
    resultat = runner.invoke(app, ["installer"])

    assert resultat.exit_code == 4
