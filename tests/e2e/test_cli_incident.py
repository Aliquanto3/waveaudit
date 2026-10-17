"""CLI de la commande `incident` de bout en bout (contrats §4, §12, §21 « CLI »), faux moteur.

Toujours `--annee 2026` : aucun test ne dépend de l'année courante. Chaque test écrit sa propre
configuration TOML sous `tmp_path` (aucun test n'écrit dans le `var/` du dépôt, AD-10).
"""

from tests.e2e.test_cli import BANDEAU, _ecrire_config, app, runner
from waveaudit.application.config import racine_projet
from waveaudit.securite import garde_reseau

DEMO = racine_projet() / "donnees" / "demo" / "incident"
ANNEE = "2026"


def test_incident_nominal_demo_bandeau_et_garde(tmp_path, faux_moteur):
    config = _ecrire_config(tmp_path, base_url=faux_moteur().base_url)
    resultat = runner.invoke(
        app, ["incident", str(DEMO), "--annee", ANNEE, "--config", str(config)]
    )

    assert resultat.exit_code == 0, resultat.output
    lignes = resultat.output.splitlines()
    assert lignes[0] == BANDEAU
    assert lignes[-1] == BANDEAU
    lignes_recit = [ligne for ligne in lignes if ligne.startswith("[")]
    assert len(lignes_recit) == 16
    (synthese,) = [ligne for ligne in lignes if "rapport :" in ligne]
    assert "rapport : rapport-incident.docx (lot " in synthese
    assert str(tmp_path) not in resultat.output
    assert not garde_reseau._actif


def test_incident_dossier_absent_code_2(tmp_path, faux_moteur):
    config = _ecrire_config(tmp_path, base_url=faux_moteur().base_url)
    resultat = runner.invoke(
        app,
        ["incident", str(tmp_path / "absent"), "--annee", ANNEE, "--config", str(config)],
    )

    assert resultat.exit_code == 2
    assert resultat.output.strip()
    assert str(tmp_path) not in resultat.output
    assert not garde_reseau._actif


def test_incident_dossier_sans_fichier_route_code_2(tmp_path, faux_moteur):
    config = _ecrire_config(tmp_path, base_url=faux_moteur().base_url)
    dossier = tmp_path / "vide"
    dossier.mkdir()
    resultat = runner.invoke(
        app, ["incident", str(dossier), "--annee", ANNEE, "--config", str(config)]
    )

    assert resultat.exit_code == 2
    assert resultat.output.strip()
    assert not garde_reseau._actif


def test_incident_moteur_injoignable_sur_demo_code_3(tmp_path, faux_moteur):
    config = _ecrire_config(tmp_path, base_url=faux_moteur("injoignable").base_url)
    resultat = runner.invoke(
        app, ["incident", str(DEMO), "--annee", ANNEE, "--config", str(config)]
    )

    assert resultat.exit_code == 3
    assert not garde_reseau._actif


def test_incident_moteur_injoignable_sans_detection_code_0(tmp_path, faux_moteur):
    """Aucune détection : le moteur n'est jamais ouvert, même injoignable (contrats §21)."""
    config = _ecrire_config(tmp_path, base_url=faux_moteur("injoignable").base_url)
    dossier = tmp_path / "journaux"
    dossier.mkdir()
    (dossier / "auth.log").write_text(
        "Oct 14 08:00:01 BASTION01 sshd[100]: Server listening on 0.0.0.0 port 22.\n",
        encoding="utf-8",
    )
    resultat = runner.invoke(
        app, ["incident", str(dossier), "--annee", ANNEE, "--config", str(config)]
    )

    assert resultat.exit_code == 0, resultat.output
    assert not garde_reseau._actif


def test_incident_sortie_verrouillee_code_4(tmp_path, faux_moteur):
    config = _ecrire_config(tmp_path, base_url=faux_moteur().base_url)
    verrou = tmp_path / "verrou"
    verrou.mkdir()  # copyfile vers un dossier existant lève PermissionError sous Windows
    resultat = runner.invoke(
        app,
        ["incident", str(DEMO), "--annee", ANNEE, "--config", str(config), "-o", str(verrou)],
    )

    assert resultat.exit_code == 4
    assert "accès refusé" in resultat.output
    assert "(verrou)" in resultat.output  # la cible, pas le fichier provisoire `.partiel`
    assert "partiel" not in resultat.output
    assert str(tmp_path) not in resultat.output


def _dossier_sans_detection(tmp_path):
    dossier = tmp_path / "journaux"
    dossier.mkdir()
    (dossier / "auth.log").write_text(
        "Oct 14 08:00:01 BASTION01 sshd[100]: Server listening on 0.0.0.0 port 22.\n",
        encoding="utf-8",
    )
    return dossier


def test_incident_modele_inconnu_local_gere_sans_detection_code_2(tmp_path):
    """Sans détection le moteur n'est pas ouvert, mais `--modele` inconnu donne 2 (§4, §19)."""
    config = _ecrire_config(tmp_path, mode="local-gere")
    resultat = runner.invoke(
        app,
        [
            "incident",
            str(_dossier_sans_detection(tmp_path)),
            "--annee",
            ANNEE,
            "--config",
            str(config),
            "--modele",
            "inconnu-xyz",
        ],
    )

    assert resultat.exit_code == 2
    assert "inconnu-xyz" in resultat.output
    assert not garde_reseau._actif


def test_incident_modele_inconnu_local_gere_demo_code_2(tmp_path):
    config = _ecrire_config(tmp_path, mode="local-gere")
    resultat = runner.invoke(
        app,
        ["incident", str(DEMO), "--annee", ANNEE, "--config", str(config), "--modele", "x-y"],
    )

    assert resultat.exit_code == 2


def test_incident_modele_externe_surcharge(tmp_path, faux_moteur):
    import json

    moteur = faux_moteur()
    config = _ecrire_config(tmp_path, base_url=moteur.base_url)
    resultat = runner.invoke(
        app,
        [
            "incident",
            str(DEMO),
            "--annee",
            ANNEE,
            "--config",
            str(config),
            "--modele",
            "mon-modele",
        ],
    )

    assert resultat.exit_code == 0, resultat.output
    (journal,) = (tmp_path / "var" / "sorties").glob("*/journal.jsonl")
    demarre = json.loads(journal.read_text(encoding="utf-8").splitlines()[0])
    assert demarre["type"] == "lot_demarre"
    assert moteur.requetes
    assert {corps["model"] for corps in moteur.requetes} == {"mon-modele"}
