"""Garde réseau (contrats §12, AD-9). Seule défense contre un appel sortant introduit par une
dépendance sans que rien le détecte.

`activer(hotes)` remplace `socket.socket.connect`, `socket.socket.connect_ex`,
`socket.create_connection` et, pour l'UDP non connecté, `socket.socket.sendto` et
`socket.socket.sendmsg` (s'il existe) par des versions qui vérifient la destination avant de
transmettre l'appel à la fonction d'origine : une destination hors liste lève `ConnexionInterdite`
sans jamais atteindre la fonction remplacée (ni, donc, pytest-socket en test).

Une destination est autorisée si c'est une IP résolue depuis la liste, ou un nom de la liste tel
quel (`localhost`) : un nom absent de la liste est refusé sans résolution DNS.
"""

import socket
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

from waveaudit.domaine.erreurs import ConnexionInterdite

_verrou = threading.Lock()
_actif = False
_autorises: frozenset[str] = frozenset()
_tentatives: list[tuple[str, int]] = []
# Gardé après `desactiver()` : une fonction remplacée capturée sous garde (`from socket import
# create_connection`) reste appelable ensuite et transmet alors directement.
_originaux: dict[str, Callable[..., Any]] = {}


def _normaliser(hote: str) -> str:
    return hote.casefold().rstrip(".")


def _resoudre(hotes: list[str]) -> frozenset[str]:
    autorises: set[str] = set()
    for hote in hotes:
        autorises.add(_normaliser(hote))
        for info in socket.getaddrinfo(hote, None):
            autorises.add(_normaliser(str(info[4][0])))
    return frozenset(autorises)


def _verifier(adresse: Any) -> None:
    if not _actif or not isinstance(adresse, tuple) or len(adresse) < 2:
        return
    hote, port = adresse[0], adresse[1]
    if isinstance(hote, bytes):
        hote = hote.decode("ascii", "replace")
    if _normaliser(str(hote)) not in _autorises:
        _tentatives.append((str(hote), port))
        raise ConnexionInterdite(f"connexion interdite vers {hote}:{port}")


def _connect_garde(soi: socket.socket, adresse: Any) -> Any:
    _verifier(adresse)
    return _originaux["connect"](soi, adresse)


def _connect_ex_garde(soi: socket.socket, adresse: Any) -> Any:
    _verifier(adresse)
    return _originaux["connect_ex"](soi, adresse)


def _create_connection_garde(adresse: Any, *args: Any, **kwargs: Any) -> Any:
    _verifier(adresse)
    return _originaux["create_connection"](adresse, *args, **kwargs)


def _sendto_garde(soi: socket.socket, *args: Any) -> Any:
    # sendto(data, adresse) ou sendto(data, flags, adresse).
    if len(args) >= 2:
        _verifier(args[-1])
    return _originaux["sendto"](soi, *args)


def _sendmsg_garde(soi: socket.socket, *args: Any) -> Any:
    # sendmsg(buffers, ancdata, flags, adresse).
    if len(args) >= 4:
        _verifier(args[3])
    return _originaux["sendmsg"](soi, *args)


_REMPLACEMENTS: dict[str, tuple[Any, Callable[..., Any]]] = {
    "connect": (socket.socket, _connect_garde),
    "connect_ex": (socket.socket, _connect_ex_garde),
    "create_connection": (socket, _create_connection_garde),
    "sendto": (socket.socket, _sendto_garde),
}
if hasattr(socket.socket, "sendmsg"):  # absent sous Windows
    _REMPLACEMENTS["sendmsg"] = (socket.socket, _sendmsg_garde)


def activer(hotes: list[str]) -> None:
    """Active le garde pour les hôtes donnés (contrats §12). Idempotente.

    Résout chaque hôte par `getaddrinfo`, puis, si le garde n'est pas déjà actif, sauvegarde et
    remplace les fonctions réseau. Réinitialise `tentatives()`.
    """
    global _actif, _autorises
    autorises = _resoudre(hotes)
    with _verrou:
        _autorises = autorises
        _tentatives.clear()
        if _actif:
            return
        for nom, (porteur, remplacement) in _REMPLACEMENTS.items():
            _originaux[nom] = getattr(porteur, nom)
            setattr(porteur, nom, remplacement)
        _actif = True


def desactiver() -> None:
    """Restaure les fonctions réseau sauvegardées (contrats §12). Sans effet si déjà inactif."""
    global _actif
    with _verrou:
        if not _actif:
            return
        for nom, (porteur, _) in _REMPLACEMENTS.items():
            setattr(porteur, nom, _originaux[nom])
        _actif = False


def tentatives() -> list[tuple[str, int]]:
    """Connexions refusées depuis la dernière activation (contrats §12)."""
    return list(_tentatives)


@contextmanager
def garde(hotes: list[str]) -> Iterator[None]:
    """Active le garde pour la durée du bloc, puis le désactive (contrats §12).

    Imbriqué dans un garde déjà actif (test e2e autour d'une commande qui pose son propre garde),
    il ajoute ses hôtes pour la durée du bloc sans réinitialiser `tentatives()`, puis rend la
    liste précédente au lieu de désactiver le garde englobant.
    """
    global _autorises
    with _verrou:
        englobant = _actif
        precedents = _autorises
    if not englobant:
        activer(hotes)
        try:
            yield
        finally:
            desactiver()
        return
    ajout = _resoudre(hotes)
    with _verrou:
        _autorises = precedents | ajout
    try:
        yield
    finally:
        with _verrou:
            _autorises = precedents
