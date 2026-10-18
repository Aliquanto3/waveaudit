"""Lifespan de l'UI à l'arrêt (contrats §24, AD-20, ARR) : jamais de vrai llama-server.

Story ARR : si l'arrêt de l'UI survient pendant une ouverture de llama-server (régénération),
le lifespan ne doit pas dépasser `ATTENTE_ARRET_MOTEUR_S` ; au-delà, le llama-server en cours
d'ouverture est terminé directement plutôt qu'attendu (`MoteurALaDemande.fermer(timeout=...)`).
"""

import threading
import time
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from tests.unitaires.test_composition import GO, _FauxServeur, _installer, _local
from waveaudit.adaptateurs import memoire_psutil
from waveaudit.application import composition
from waveaudit.application.moteur_demande import Occupation
from waveaudit.domaine.erreurs import MoteurInjoignable
from waveaudit.installation import manifeste
from waveaudit.interfaces.web import app as app_module

BINAIRE = "llama-server-b11714"
MODELE = "granite-4.0-1b-q4km"


def test_lifespan_arret_pendant_ouverture_lente_reste_dans_la_borne(config_test, monkeypatch):
    """Ouverture bloquée au-delà du délai d'arrêt : le lifespan rend la main dans la borne et
    force l'arrêt du llama-server en cours (filet `composition.terminer_llama_server_en_cours`).
    """
    monkeypatch.setattr(memoire_psutil, "ram_disponible_octets", lambda: 16 * GO)
    # Borne raccourcie pour un test rapide, sondage borné plutôt qu'une attente longue.
    monkeypatch.setattr(app_module, "ATTENTE_ARRET_MOTEUR_S", 0.3)
    artefacts = manifeste.charger(config_test.chemins.manifeste)
    defaut = manifeste.par_role(artefacts, "modele_defaut").nom
    _installer(config_test, artefacts, BINAIRE, defaut)
    config = _local(config_test)

    abandon = threading.Event()
    appels: list[None] = []
    original_terminer = composition.terminer_llama_server_en_cours

    class ServeurLent(_FauxServeur):
        def __enter__(self):
            if not abandon.wait(timeout=5):
                pytest.fail("terminer_llama_server_en_cours pas appelé dans le délai")
            raise MoteurInjoignable("arrêt forcé pendant l'ouverture")

    def terminer() -> None:
        appels.append(None)
        abandon.set()
        original_terminer()

    monkeypatch.setattr(composition, "LlamaServer", ServeurLent)
    monkeypatch.setattr(composition, "terminer_llama_server_en_cours", terminer)

    app = app_module.creer_app(config, hotes_test=("testserver",))
    erreurs: list[BaseException] = []

    def ouvrir() -> None:
        try:
            with app.state.moteur.utiliser(MODELE):
                pytest.fail("l'ouverture ne doit pas réussir")
        except BaseException as exc:  # noqa: BLE001 - remonté par l'assertion
            erreurs.append(exc)

    duree = None
    with TestClient(app, base_url="http://testserver"):
        assert app.state.verrou.prendre(Occupation("regeneration", "lot-1", 0, datetime.now()))
        fil = threading.Thread(target=ouvrir, daemon=True)
        fil.start()
        limite = time.monotonic() + 5
        while not app.state.moteur._verrou.locked() and time.monotonic() < limite:
            time.sleep(0.01)
        assert app.state.moteur._verrou.locked(), "l'ouverture n'a pas pris le verrou interne"
        debut = time.monotonic()
    duree = time.monotonic() - debut

    fil.join(timeout=5)
    assert not fil.is_alive()
    assert duree < 2.0, f"lifespan trop long : {duree} s"
    assert appels, "le filet n'a pas été déclenché"
    assert erreurs and isinstance(erreurs[0], MoteurInjoignable)


def test_lifespan_arret_pendant_ouverture_vrai_llama_server_sans_orphelin(config_test, monkeypatch):
    """[revue ARR] Chaîne réelle, sans doublure du filet : lifespan -> `fermer(timeout)` ->
    `terminer_tous` -> vrai `LlamaServer._attendre` sur un faux binaire qui ne répond jamais à
    `/health`. L'ouverture lève `MoteurInjoignable`, le lifespan tient sa borne et le
    sous-processus est terminé."""
    import sys
    from pathlib import Path

    import psutil

    from waveaudit.adaptateurs.llama_server import LlamaServer

    tests = Path(__file__).resolve().parents[1]
    python = Path(getattr(sys, "_base_executable", sys.executable))
    monkeypatch.setenv("PYTHONPATH", str(tests))
    monkeypatch.setenv("FAUX_LLAMA_SCENARIO", "jamais_pret")
    monkeypatch.setattr(memoire_psutil, "ram_disponible_octets", lambda: 16 * GO)
    monkeypatch.setattr(app_module, "ATTENTE_ARRET_MOTEUR_S", 0.5)
    artefacts = manifeste.charger(config_test.chemins.manifeste)
    defaut = manifeste.par_role(artefacts, "modele_defaut").nom
    _installer(config_test, artefacts, BINAIRE, defaut)
    config = _local(config_test)
    serveurs: list[LlamaServer] = []

    class ServeurFaux(LlamaServer):
        def __init__(self, binaire, gguf, ctx, threads, delai_s, journal):
            super().__init__(python, Path("faux_llama_server"), ctx, threads, 60.0, journal)
            serveurs.append(self)

    monkeypatch.setattr(composition, "LlamaServer", ServeurFaux)
    app = app_module.creer_app(config, hotes_test=("testserver",))
    erreurs: list[BaseException] = []

    def ouvrir() -> None:
        try:
            with app.state.moteur.utiliser(MODELE):
                pass
        except BaseException as exc:  # noqa: BLE001 - remonté par l'assertion
            erreurs.append(exc)

    with TestClient(app, base_url="http://testserver"):
        fil = threading.Thread(target=ouvrir, daemon=True)
        fil.start()
        limite = time.monotonic() + 10
        while not (serveurs and serveurs[0]._processus) and time.monotonic() < limite:
            time.sleep(0.05)
        pid = serveurs[0].pid
        debut = time.monotonic()
    duree = time.monotonic() - debut
    fil.join(timeout=10)
    assert not fil.is_alive()
    assert duree < 5.0, f"lifespan trop long : {duree} s"
    assert erreurs and isinstance(erreurs[0], MoteurInjoignable), erreurs
    try:
        etat = psutil.Process(pid).status()
    except psutil.NoSuchProcess:
        etat = None
    assert etat in (None, psutil.STATUS_ZOMBIE), "llama-server encore en vie après le lifespan"
