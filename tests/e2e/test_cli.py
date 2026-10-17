"""CLI de bout en bout (contrats §4, §12, §19), `typer.testing.CliRunner`, faux moteur.

Chaque test de `fiches` écrit sa propre configuration TOML sous `tmp_path` et la passe par
`--config` ; aucun test n'écrit dans le `var/` du dépôt (AD-10).
"""

import json
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
