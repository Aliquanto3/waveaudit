"""Garde réseau (contrats §12, AD-9). Seule défense contre un appel sortant introduit par une
dépendance sans que rien le détecte.

`activer(hotes)` remplace `socket.socket.connect`, `socket.socket.connect_ex` et
`socket.create_connection` par des versions qui vérifient l'adresse de destination avant de
transmettre l'appel à la fonction d'origine : une adresse hors liste lève `ConnexionInterdite`
sans jamais atteindre la fonction remplacée (ni, donc, pytest-socket en test).
"""

import socket
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

from waveaudit.domaine.erreurs import ConnexionInterdite

_verrou = threading.Lock()
_actif = False
_ips_autorisees: frozenset[str] = frozenset()
_tentatives: list[tuple[str, int]] = []
_originaux: dict[str, Callable[..., Any]] = {}


def _resoudre(hotes: list[str]) -> frozenset[str]:
    ips: set[str] = set()
    for hote in hotes:
        for info in socket.getaddrinfo(hote, None):
            ips.add(info[4][0])
    return frozenset(ips)


def _verifier(hote: str, port: int) -> None:
    if hote not in _ips_autorisees:
        _tentatives.append((hote, port))
        raise ConnexionInterdite(f"connexion interdite vers {hote}:{port}")


def _connect_garde(soi: socket.socket, adresse: Any) -> Any:
    if isinstance(adresse, tuple) and len(adresse) >= 2:
        _verifier(adresse[0], adresse[1])
    return _originaux["connect"](soi, adresse)


def _connect_ex_garde(soi: socket.socket, adresse: Any) -> Any:
    if isinstance(adresse, tuple) and len(adresse) >= 2:
        _verifier(adresse[0], adresse[1])
    return _originaux["connect_ex"](soi, adresse)


def _create_connection_garde(adresse: tuple[str, int], *args: Any, **kwargs: Any) -> Any:
    _verifier(adresse[0], adresse[1])
    return _originaux["create_connection"](adresse, *args, **kwargs)


def activer(hotes: list[str]) -> None:
    """Active le garde pour les hôtes donnés (contrats §12). Idempotente.

    Résout chaque hôte par `getaddrinfo`, puis, si le garde n'est pas déjà actif, sauvegarde et
    remplace les fonctions réseau. Réinitialise `tentatives()`.
    """
    global _actif, _ips_autorisees
    ips = _resoudre(hotes)
    with _verrou:
        _ips_autorisees = ips
        _tentatives.clear()
        if _actif:
            return
        _originaux["connect"] = socket.socket.connect
        _originaux["connect_ex"] = socket.socket.connect_ex
        _originaux["create_connection"] = socket.create_connection
        socket.socket.connect = _connect_garde  # type: ignore[method-assign]
        socket.socket.connect_ex = _connect_ex_garde  # type: ignore[method-assign]
        socket.create_connection = _create_connection_garde  # type: ignore[assignment]
        _actif = True


def desactiver() -> None:
    """Restaure les fonctions réseau sauvegardées (contrats §12). Sans effet si déjà inactif."""
    global _actif
    with _verrou:
        if not _actif:
            return
        socket.socket.connect = _originaux["connect"]  # type: ignore[method-assign]
        socket.socket.connect_ex = _originaux["connect_ex"]  # type: ignore[method-assign]
        socket.create_connection = _originaux["create_connection"]  # type: ignore[assignment]
        _originaux.clear()
        _actif = False


def tentatives() -> list[tuple[str, int]]:
    """Connexions refusées depuis la dernière activation (contrats §12)."""
    return list(_tentatives)


@contextmanager
def garde(hotes: list[str]) -> Iterator[None]:
    """Active le garde pour la durée du bloc, puis le désactive (contrats §12)."""
    activer(hotes)
    try:
        yield
    finally:
        desactiver()
