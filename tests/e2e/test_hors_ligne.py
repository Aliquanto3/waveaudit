"""Preuve hors ligne de bout en bout (CAP-11, contrats §12).

Un lot CLI et un lot UI complets, lancés sous `garde()` (la commande CLI l'active, comme en
exploitation réelle), ne déclenchent aucune tentative de connexion hors boucle locale
(`garde_reseau.tentatives() == []`). Deux tests négatifs prouvent que le garde refuse une
connexion vers une adresse hors liste (192.0.2.1, TEST-NET-1 de la RFC 5737, jamais routée)
avant qu'elle n'atteigne le réseau : depuis un abonné du vrai lot, et depuis la commande (code 4).
"""

import time
from typing import Any

from tests.e2e.test_cli import DEMO, _ecrire_config, app, runner
from tests.e2e.test_cli_incident import DEMO as DEMO_INCIDENT
from tests.e2e.test_ui import _attendre_fin, _notes_demo
from tests.web_outils import client as client_web
from waveaudit.domaine.erreurs import ConnexionInterdite
from waveaudit.domaine.modeles import TypeEvenement
from waveaudit.securite import garde_reseau


def test_cli_lot_sous_garde_sans_tentative(tmp_path, faux_moteur):
    config = _ecrire_config(tmp_path, base_url=faux_moteur().base_url)
    resultat = runner.invoke(app, ["fiches", str(DEMO), "--config", str(config)])

    assert resultat.exit_code == 0, resultat.output
    assert garde_reseau.tentatives() == []
    assert not garde_reseau._actif


def test_cli_incident_sous_garde_sans_tentative(tmp_path, faux_moteur):
    config = _ecrire_config(tmp_path, base_url=faux_moteur().base_url)
    resultat = runner.invoke(
        app, ["incident", str(DEMO_INCIDENT), "--annee", "2026", "--config", str(config)]
    )

    assert resultat.exit_code == 0, resultat.output
    assert garde_reseau.tentatives() == []
    assert not garde_reseau._actif


def test_ui_lot_sous_garde_sans_tentative(monkeypatch, tmp_path, faux_moteur):
    """`uvicorn.run` est remplacé, mais appelé à l'intérieur du `with garde(...)` de la commande
    `ui` (contrats §12) : le lot posté pendant cet appel tourne donc réellement sous le garde."""
    config = _ecrire_config(tmp_path, base_url=faux_moteur().base_url)
    capture: dict[str, Any] = {}

    def faux_run(application: Any, *, host: str, port: int) -> None:
        capture["garde_actif_au_demarrage"] = garde_reseau._actif
        # Application réelle de la commande `ui` : pas de `testserver`, Host de boucle locale.
        client = client_web(application, base_url=f"http://127.0.0.1:{port}")
        reponse = client.post("/lots", files=_notes_demo(), follow_redirects=False)
        id_lot = reponse.headers["location"].rsplit("/", 1)[-1]
        capture["etat"] = _attendre_fin(client, id_lot)

    monkeypatch.setattr("uvicorn.run", faux_run)
    resultat = runner.invoke(app, ["ui", "--config", str(config)])

    assert resultat.exit_code == 0, resultat.output
    assert capture["garde_actif_au_demarrage"]
    assert capture["etat"]["etat"] == "termine"
    assert garde_reseau.tentatives() == []
    assert not garde_reseau._actif


def test_ui_changement_de_candidat_sous_garde_sans_tentative(monkeypatch, tmp_path, faux_moteur):
    """[v2] Relecture (W3a) : la régénération d'une fiche par changement de candidat tourne sous
    le `garde(...)` de la commande `ui`, comme le lot, sans tentative hors boucle locale."""
    config = _ecrire_config(tmp_path, base_url=faux_moteur().base_url)
    capture: dict[str, Any] = {}

    def faux_run(application: Any, *, host: str, port: int) -> None:
        client = client_web(application, base_url=f"http://127.0.0.1:{port}")
        reponse = client.post("/lots", files=_notes_demo()[:1], follow_redirects=False)
        id_lot = reponse.headers["location"].rsplit("/", 1)[-1]
        _attendre_fin(client, id_lot)
        entree = client.get(f"/lots/{id_lot}/entrees/1").json()["entree"]
        autre = next(c["id"] for c in entree["candidats"] if c["id"] != entree["candidat_choisi"])
        capture["statut"] = client.post(
            f"/lots/{id_lot}/entrees/1/candidat",
            json={"version": entree["version"], "constat_id": autre},
        ).status_code
        limite = time.monotonic() + 10
        while application.state.verrou.occupation() is not None and time.monotonic() < limite:
            time.sleep(0.05)
        capture["entree"] = client.get(f"/lots/{id_lot}/entrees/1").json()["entree"]
        capture["autre"] = autre
        capture["garde_actif"] = garde_reseau._actif

    monkeypatch.setattr("uvicorn.run", faux_run)
    resultat = runner.invoke(app, ["ui", "--config", str(config)])

    assert resultat.exit_code == 0, resultat.output
    assert capture["garde_actif"]
    assert capture["statut"] == 202
    assert capture["entree"]["generation"] == "aucune"
    assert capture["entree"]["candidat_choisi"] == capture["autre"]
    assert garde_reseau.tentatives() == []
    assert not garde_reseau._actif


def test_negatif_connexion_hors_boucle_locale_refusee(monkeypatch, tmp_path, faux_moteur):
    """Un abonné du vrai lot (code tiers appelé à chaque événement) tente de joindre 192.0.2.1 :
    le garde lève avant toute connexion réelle et enregistre la tentative. Le lot ignore les
    erreurs d'abonné (AD-6) : la commande se termine donc normalement, mais rien n'est sorti."""
    import socket

    import waveaudit.application.lot as lot_module

    executer_lot_reel = lot_module.executer_lot
    erreurs: list[BaseException] = []

    def executer_lot_avec_abonne_malicieux(requete: Any, config: Any, abonne: Any = None) -> Any:
        def malicieux(evenement: Any) -> None:
            if abonne is not None:
                abonne(evenement)
            if evenement.type == TypeEvenement.LOT_DEMARRE:
                try:
                    socket.create_connection(("192.0.2.1", 80), timeout=0.2)
                except BaseException as erreur:
                    erreurs.append(erreur)
                    raise

        return executer_lot_reel(requete, config, malicieux)

    monkeypatch.setattr(lot_module, "executer_lot", executer_lot_avec_abonne_malicieux)
    config = _ecrire_config(tmp_path, base_url=faux_moteur().base_url)
    resultat = runner.invoke(app, ["fiches", str(DEMO), "--config", str(config)])

    assert resultat.exit_code == 0, resultat.output
    assert len(erreurs) == 1 and isinstance(erreurs[0], ConnexionInterdite)
    assert garde_reseau.tentatives() == [("192.0.2.1", 80)]
    assert not garde_reseau._actif


def test_negatif_connexion_hors_boucle_locale_code_retour_4(monkeypatch, tmp_path, faux_moteur):
    """Une connexion interdite qui remonte jusqu'à la commande (hors abonné) donne le code 4."""
    import socket

    import waveaudit.application.lot as lot_module

    def executer_lot_qui_se_connecte(requete: Any, config: Any, abonne: Any = None) -> None:
        socket.create_connection(("192.0.2.1", 80), timeout=0.2)
        raise AssertionError("jamais atteint : le garde doit lever avant la connexion")

    monkeypatch.setattr(lot_module, "executer_lot", executer_lot_qui_se_connecte)
    config = _ecrire_config(tmp_path, base_url=faux_moteur().base_url)
    resultat = runner.invoke(app, ["fiches", str(DEMO), "--config", str(config)])

    assert resultat.exit_code == 4, resultat.output
    assert "192.0.2.1" in resultat.output
    assert garde_reseau.tentatives() == [("192.0.2.1", 80)]
    assert not garde_reseau._actif
