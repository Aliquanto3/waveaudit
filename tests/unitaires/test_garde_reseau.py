"""Tests du garde réseau (contrats §12, AD-9). Aucune connexion réelle hors loopback."""

import socket
from urllib.parse import urlsplit

import pytest

from waveaudit.domaine.erreurs import ConnexionInterdite
from waveaudit.securite import garde_reseau


def _fonctions_reseau() -> dict[str, object]:
    return {nom: getattr(porteur, nom) for nom, (porteur, _) in garde_reseau._REMPLACEMENTS.items()}


@pytest.fixture(autouse=True)
def _aucune_fuite_entre_tests():
    """Après chaque test, aucune fonction réseau n'est un remplacement du garde : le test doit
    désactiver lui-même. On ne compare pas à la valeur d'avant le test, car pytest-socket
    (`--allow-hosts`) pose et retire son propre `connect` autour du test."""
    yield
    remplacements = {id(f) for _, f in garde_reseau._REMPLACEMENTS.values()}
    try:
        assert not garde_reseau._actif, "garde laissé actif par le test"
        fuites = [nom for nom, f in _fonctions_reseau().items() if id(f) in remplacements]
        assert fuites == [], f"fonctions encore remplacées : {fuites}"
    finally:
        garde_reseau.desactiver()


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


def test_connect_ex_hors_liste_refuse():
    with garde_reseau.garde(["127.0.0.1"]):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as brut:
            with pytest.raises(ConnexionInterdite):
                brut.connect_ex(("192.0.2.1", 80))
    assert garde_reseau.tentatives() == [("192.0.2.1", 80)]


def test_create_connection_vers_nom_hors_liste_refuse_sans_resolution(monkeypatch):
    def interdit(*_args, **_kwargs):
        raise AssertionError("résolution DNS sous garde")

    with garde_reseau.garde(["127.0.0.1"]):
        monkeypatch.setattr(socket, "getaddrinfo", interdit)
        with pytest.raises(ConnexionInterdite):
            socket.create_connection(("exemple.invalid", 443), timeout=1)
    assert garde_reseau.tentatives() == [("exemple.invalid", 443)]


def test_sendto_udp_hors_liste_refuse():
    with garde_reseau.garde(["127.0.0.1"]):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
            with pytest.raises(ConnexionInterdite):
                udp.sendto(b"x", ("192.0.2.1", 53))
            with pytest.raises(ConnexionInterdite):
                udp.sendto(b"x", 0, ("192.0.2.1", 53))
    assert garde_reseau.tentatives() == [("192.0.2.1", 53), ("192.0.2.1", 53)]


def test_localhost_resolu_vers_127_0_0_1():
    with garde_reseau.garde(["localhost"]):
        with pytest.raises(OSError) as info:
            socket.create_connection(("127.0.0.1", 1), timeout=1)
    assert not isinstance(info.value, ConnexionInterdite)
    assert garde_reseau.tentatives() == []


def test_localhost_par_son_nom_autorise(faux_moteur):
    """Configuration par défaut : `localhost` dans la liste, base_url `http://localhost:…`."""
    _, port = _hote_port(faux_moteur().base_url)
    with garde_reseau.garde(["localhost"]):
        try:
            with socket.create_connection(("localhost", port), timeout=1):
                pass
        except ConnexionInterdite:
            raise
        except OSError:
            pass  # localhost résolu en ::1 d'abord alors que le faux moteur écoute en IPv4
    assert garde_reseau.tentatives() == []


def test_garde_imbrique_ne_desactive_pas_l_englobant():
    with garde_reseau.garde(["127.0.0.1"]):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as brut:
            with pytest.raises(ConnexionInterdite):
                brut.connect(("192.0.2.1", 80))
        with garde_reseau.garde(["127.0.0.1", "::1"]):
            pass
        assert socket.socket.connect is garde_reseau._connect_garde
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as brut:
            with pytest.raises(ConnexionInterdite):
                brut.connect(("192.0.2.2", 80))
    assert garde_reseau.tentatives() == [("192.0.2.1", 80), ("192.0.2.2", 80)]


def test_fonction_capturee_sous_garde_reste_appelable_apres():
    with garde_reseau.garde(["127.0.0.1"]):
        capturee = socket.create_connection
    with pytest.raises(OSError) as info:
        capturee(("127.0.0.1", 1), timeout=1)
    assert not isinstance(info.value, ConnexionInterdite)


def test_activer_idempotent():
    garde_reseau.activer(["127.0.0.1", "::1"])
    fonction_connect = socket.socket.connect
    garde_reseau.activer(["127.0.0.1", "::1"])
    assert socket.socket.connect is fonction_connect
    garde_reseau.desactiver()


def test_desactiver_restaure():
    originales = _fonctions_reseau()
    garde_reseau.activer(["127.0.0.1", "::1"])
    assert socket.socket.connect is not originales["connect"]
    garde_reseau.desactiver()
    assert _fonctions_reseau() == originales


def test_desactiver_sans_garde_actif_est_sans_effet():
    original = socket.socket.connect
    garde_reseau.desactiver()
    assert socket.socket.connect is original


def test_connexion_interdite_n_est_pas_une_oserror():
    assert not issubclass(ConnexionInterdite, OSError)
