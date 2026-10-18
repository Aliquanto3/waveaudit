"""Routeur des lots de fiches (contrats §18, §26) : création, état, rapport de fin de lot.

L'état vient encore du `_RegistreLots` en mémoire de la v0.1.0 ; W2 le remplace par l'état lu
sur le disque (`application/lots.py`, AD-22). Les règles communes (Host, Origin, CSRF, taille
totale, en-têtes) sont posées par le middleware d'`app.py`.
"""

import re
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Query, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException

from waveaudit.application.lot import RAPPORT, executer_lot, nouvel_id_lot, sans_chemin
from waveaudit.domaine.configuration import Configuration
from waveaudit.domaine.modeles import EvenementLot, RequeteLot
from waveaudit.interfaces.web.commun import en_mo, erreur

routeur = APIRouter()

MAX_FICHIERS = 100  # contrats §26 [revue A5/E42]
TAILLE_MAX_FICHIER = 1024 * 1024  # 1 Mio par note
_MOTIF_NOM = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]{0,99}\.(md|txt)$", re.IGNORECASE)
_RESERVES_WINDOWS = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)
_LONGUEUR_NOM_AFFICHE = 120

EtatStr = Literal["en_cours", "termine", "echoue"]


class Refus(Exception):
    """Dépôt refusé : porte la réponse d'erreur codée (§26)."""

    def __init__(self, reponse: JSONResponse) -> None:
        super().__init__()
        self.reponse = reponse


@dataclass
class _EtatLot:
    etat: EtatStr = "en_cours"
    evenements: list[dict] = field(default_factory=list)
    erreur: str | None = None


class _RegistreLots:
    """État de chaque lot lancé par l'UI, protégé par un verrou (contrats §18 ; jusqu'à W2)."""

    def __init__(self) -> None:
        self._verrou = threading.Lock()
        self._etats: dict[str, _EtatLot] = {}

    def creer(self, id_lot: str) -> None:
        with self._verrou:
            self._etats[id_lot] = _EtatLot()

    def abonne(self, id_lot: str):
        def recevoir(evenement: EvenementLot) -> None:
            with self._verrou:
                etat = self._etats.get(id_lot)
                if etat is not None:
                    etat.evenements.append(evenement.model_dump(mode="json"))

        return recevoir

    def terminer(self, id_lot: str) -> None:
        with self._verrou:
            etat = self._etats.get(id_lot)
            if etat is not None:
                etat.etat = "termine"

    def echouer(self, id_lot: str, message: str) -> None:
        with self._verrou:
            etat = self._etats.get(id_lot)
            if etat is not None:
                etat.etat = "echoue"
                etat.erreur = message

    def lire(self, id_lot: str, depuis: int = 0) -> _EtatLot | None:
        """Copie de l'état ; `depuis` ne copie que les événements à partir de cet indice."""
        with self._verrou:
            etat = self._etats.get(id_lot)
            if etat is None:
                return None
            return _EtatLot(etat=etat.etat, evenements=etat.evenements[depuis:], erreur=etat.erreur)


class EtatLots:
    """État des lots d'une instance de l'application, posé sur `app.state.lots`."""

    def __init__(self, config: Configuration) -> None:
        self.config = config
        self.registre = _RegistreLots()
        self.verrou = threading.Lock()
        self.debut: datetime | None = None


def _nom_affiche(nom_brut: str) -> str:
    return nom_brut[:_LONGUEUR_NOM_AFFICHE]


def _valider_nom(nom_brut: str, deja_vus: set[str]) -> str:
    """Vérifie un nom de note (contrats §18, §26 [revue A6/E41]) ; renvoie le nom retenu.

    `base != nom_brut` refuse un nom qui contient un composant de chemin (`../x.md`), puisque
    `Path(nom_brut).name` en retire alors une partie.
    """
    nom = _nom_affiche(nom_brut)
    base = Path(nom_brut).name
    if base != nom_brut or base.endswith((".", " ")) or not _MOTIF_NOM.fullmatch(base):
        raise Refus(
            erreur(
                400,
                "nom_refuse",
                f"Le nom « {nom} » n'est pas accepté. Utilisez des lettres, chiffres, espaces, "
                "points ou tirets, en .md ou .txt.",
            )
        )
    # Windows résout le périphérique sur la partie avant le premier point, espaces finaux
    # retirés : `CON.x.md` et `NUL .md` sont réservés comme `CON.md`.
    if base.split(".", 1)[0].rstrip(" ").upper() in _RESERVES_WINDOWS:
        raise Refus(
            erreur(
                400,
                "nom_refuse",
                f"Le nom « {nom} » est réservé par Windows. Renommez le fichier.",
            )
        )
    # Windows retire les points et espaces finaux : `a.md` et `a.md ` désignent le même fichier.
    cle = base.rstrip(". ").casefold()
    if cle in deja_vus:
        raise Refus(
            erreur(
                400,
                "nom_refuse",
                f"Le nom « {nom} » figure deux fois dans le dépôt. Retirez le doublon.",
            )
        )
    deja_vus.add(cle)
    return base


async def _valider_notes(fichiers: list[UploadFile]) -> list[tuple[str, bytes]]:
    """Valide et lit chaque note envoyée (§18, §26) ; lève `Refus` au premier refus."""
    if not fichiers:
        raise Refus(erreur(400, "aucune_note", "Aucune note dans le dépôt."))
    if len(fichiers) > MAX_FICHIERS:
        raise Refus(
            erreur(
                400,
                "trop_de_fichiers",
                f"Le dépôt compte {len(fichiers)} fichiers ; {MAX_FICHIERS} au plus par lot.",
            )
        )
    deja_vus: set[str] = set()
    noms = [_valider_nom(fichier.filename or "", deja_vus) for fichier in fichiers]
    resultat: list[tuple[str, bytes]] = []
    for nom, fichier in zip(noms, fichiers, strict=True):
        contenu = await fichier.read(TAILLE_MAX_FICHIER + 1)
        if len(contenu) > TAILLE_MAX_FICHIER:
            taille = fichier.size if fichier.size is not None else len(contenu)
            raise Refus(
                erreur(
                    413,
                    "trop_volumineux",
                    f"Ce fichier dépasse 1 Mo ({nom}, {en_mo(taille)}). Réduisez-le ou "
                    "retirez-le du dépôt.",
                    limite="fichier",
                )
            )
        resultat.append((nom, contenu))
    return resultat


def _lots(request: Request) -> EtatLots:
    return request.app.state.lots


def _executer_en_fond(lots: EtatLots, id_lot: str, dossier_entree: Path) -> None:
    try:
        try:
            requete = RequeteLot(dossier=dossier_entree, id_lot=id_lot)
            executer_lot(requete, lots.config, lots.registre.abonne(id_lot))
            lots.registre.terminer(id_lot)
        except Exception as exc:  # noqa: BLE001 - reporté à l'état du lot, pas relevé
            lots.registre.echouer(id_lot, sans_chemin(str(exc)))
    finally:
        lots.debut = None
        lots.verrou.release()


@routeur.post("/lots")
async def creer_lot(request: Request) -> Response:
    lots = _lots(request)
    if not lots.verrou.acquire(blocking=False):
        debut = lots.debut.strftime("%H:%M") if lots.debut else "--:--"
        return erreur(
            409,
            "lot_en_cours",
            f"Un lot est déjà en cours (lancé à {debut}). Attendez sa fin ou reprenez-le.",
        )
    # Toute sortie avant le démarrage du thread (multipart malformé, refus, erreur disque)
    # relâche le verrou ; ensuite c'est le `finally` du thread qui le relâche.
    lance = False
    try:
        lots.debut = datetime.now()
        try:
            formulaire = await request.form()
        except HTTPException as exc:
            if "too many files" in str(exc.detail).casefold():
                return erreur(
                    400,
                    "trop_de_fichiers",
                    f"Le dépôt compte trop de fichiers ; {MAX_FICHIERS} au plus par lot.",
                )
            return erreur(400, "corps_invalide", "Formulaire d'envoi illisible.")
        notes = [v for v in formulaire.getlist("notes") if isinstance(v, UploadFile)]
        try:
            fichiers = await _valider_notes(notes)
        except Refus as refus:
            return refus.reponse
        config = lots.config
        id_lot = nouvel_id_lot(config.chemins.var)
        dossier_entree = config.chemins.var / "entrees" / id_lot
        dossier_entree.mkdir(parents=True, exist_ok=True)
        for nom, contenu in fichiers:
            (dossier_entree / nom).write_bytes(contenu)
        lots.registre.creer(id_lot)
        fil = threading.Thread(
            target=_executer_en_fond, args=(lots, id_lot, dossier_entree), daemon=True
        )
        try:
            fil.start()
        except RuntimeError as exc:
            lots.registre.echouer(id_lot, str(exc))
            raise
        lance = True
        return RedirectResponse(f"/lots/{id_lot}", status_code=303)
    finally:
        if not lance:
            lots.debut = None
            lots.verrou.release()


@routeur.get("/lots/{id_lot}/etat")
def etat_lot(request: Request, id_lot: str, depuis: int = Query(0, ge=0)) -> JSONResponse:
    # `depuis` (facultatif) : le JS ne redemande que les nouveaux événements à chaque
    # interrogation, sans recopier tout le journal du lot ; 0 donne la réponse complète.
    etat = _lots(request).registre.lire(id_lot, depuis)
    if etat is None:
        return erreur(404, "lot_inconnu", "Lot inconnu.")
    return JSONResponse(
        {
            "id_lot": id_lot,
            "etat": etat.etat,
            "evenements": etat.evenements,
            "erreur": etat.erreur,
        }
    )


@routeur.get("/lots/{id_lot}/rapport.docx")
def rapport_lot(request: Request, id_lot: str) -> Response:
    lots = _lots(request)
    etat = lots.registre.lire(id_lot)
    if etat is None:
        return erreur(404, "lot_inconnu", "Lot inconnu.")
    if etat.etat != "termine":
        return erreur(409, "lot_non_termine", "Le lot n'est pas terminé.")
    chemin = lots.config.chemins.var / "sorties" / id_lot / RAPPORT
    if not chemin.is_file():
        return erreur(404, "introuvable", "Rapport introuvable.")
    return FileResponse(
        chemin,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=RAPPORT,
    )
