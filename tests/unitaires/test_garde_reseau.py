"""Tests du garde réseau (contrats §12, AD-9). Aucune connexion réelle hors loopback."""

import socket
from urllib.parse import urlsplit

import pytest

from waveaudit.domaine.erreurs import ConnexionInterdite
from waveaudit.securite import garde_reseau


@pytest.fixture(autouse=True)
def _aucune_fuite_entre_tests():
    """Le garde doit être désactivé à la fin de chaque test, même en cas d'échec."""
    yield
    garde_reseau.desactiver()
    assert socket.socket.connect is not garde_reseau._connect_garde
    assert socket.socket.connect_ex is not garde_reseau._connect_ex_garde
    assert socket.create_connection is not garde_reseau._create_connection_garde


def _hote_port(base_url: str) -> tuple[str, int]:
    morceaux = urlsplit(base_url)
    assert morceaux.hostname is not None
    assert morceaux.port is not None
    return morceaux.hostname, morceaux.port


def test_connexion_vers_faux_moteur_autorisee_sous_garde(faux_moteur):
    hote, port = _hote_port(faux_moteur().base_url)
    with garde_reseau.garde(["127.0.0.1", "::1"]):
        with socket.create_connection((hote, port), timeout=1):
            pass
    assert garde_reseau.tentatives() == []


def test_connexion_hors_liste_refusee_avant_toute_emission():
    with garde_reseau.garde(["127.0.0.1", "::1"]):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as brut:
            with pytest.raises(ConnexionInterdite):
                brut.connect(("192.0.2.1", 80))
    assert garde_reseau.tentatives() == [("192.0.2.1", 80)]


def test_localhost_resolu_vers_127_0_0_1():
    with garde_reseau.garde(["localhost"]):
        with pytest.raises(OSError) as info:
            socket.create_connection(("127.0.0.1", 1), timeout=1)
    assert not isinstance(info.value, ConnexionInterdite)
    assert garde_reseau.tentatives() == []


def test_activer_idempotent():
    garde_reseau.activer(["127.0.0.1", "::1"])
    fonction_connect = socket.socket.connect
    garde_reseau.activer(["127.0.0.1", "::1"])
    assert socket.socket.connect is fonction_connect


def test_desactiver_restaure():
    original = socket.socket.connect
    garde_reseau.activer(["127.0.0.1", "::1"])
    assert socket.socket.connect is not original
    garde_reseau.desactiver()
    assert socket.socket.connect is original


def test_desactiver_sans_garde_actif_est_sans_effet():
    original = socket.socket.connect
    garde_reseau.desactiver()
    assert socket.socket.connect is original


def test_connexion_interdite_n_est_pas_une_oserror():
    assert not issubclass(ConnexionInterdite, OSError)
