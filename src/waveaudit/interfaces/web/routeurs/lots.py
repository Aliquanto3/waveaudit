"""Routeur des lots de fiches (contrats §26, §30) : création, état, rapport de fin de lot.

L'état vient de `application/lots.py`, lu sur le disque (`journal.jsonl`, `lot.json`) à chaque
appel : plus aucun registre en mémoire (CAP-9, CAP-10, AD-22). Les règles communes (Host,
Origin, CSRF, taille totale, en-têtes) sont posées par le middleware d'`app.py`.
"""

import re
import shutil
import threading
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Query, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException

from waveaudit.application import composition
from waveaudit.application import lots as lots_app
from waveaudit.application.composition import ModeleInstalle
from waveaudit.application.lot import (
    RAPPORT,
    dossier_lot_existant,
    dossier_sorties,
    ecrire_fiche_lot,
    executer_lot,
    nouvel_id_lot,
)
from waveaudit.application.moteur_demande import MoteurALaDemande, Occupation, VerrouUnique
from waveaudit.domaine.configuration import Configuration
from waveaudit.domaine.modeles import Langue, RequeteLot
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
_LANGUES_VALIDES = frozenset({"fr", "en"})


class Refus(Exception):
    """Dépôt refusé : porte la réponse d'erreur codée (§26)."""

    def __init__(self, reponse: JSONResponse) -> None:
        super().__init__()
        self.reponse = reponse


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


def _config(request: Request) -> Configuration:
    return request.app.state.config


def _verrou(request: Request) -> VerrouUnique:
    return request.app.state.verrou


def _moteur(request: Request) -> MoteurALaDemande:
    return request.app.state.moteur


def _occupation_json(occupation: Occupation) -> dict:
    return {
        "nature": occupation.nature,
        "id_lot": occupation.id_lot,
        "debut": occupation.debut.isoformat(),
    }


def _refus_lot_en_cours(occupation: Occupation) -> JSONResponse:
    debut = occupation.debut.strftime("%H:%M")
    return erreur(
        409,
        "lot_en_cours",
        f"Un lot est déjà en cours (lancé à {debut}). Attendez sa fin ou reprenez-le.",
        occupation=_occupation_json(occupation),
    )


def _supprimer_dossiers_du_lot(config: Configuration, id_lot: str) -> None:
    """[revue A1/A2] Un refus après l'identifiant obtenu retire ce qui a été créé pour lui."""
    for sous in ("entrees", "sorties"):
        shutil.rmtree(config.chemins.var / sous / id_lot, ignore_errors=True)


def _resoudre_modele(
    modeles: list[ModeleInstalle], modele_brut: str
) -> tuple[str | None, JSONResponse | None]:
    """[revue E11] Le modèle `externe` affiché n'est jamais repassé tel quel au lot."""
    if not modele_brut:
        return None, None
    for modele in modeles:
        if modele.nom == modele_brut:
            return (None if modele.role == "externe" else modele.nom), None
    return None, erreur(
        422,
        "modele_indisponible",
        f"Le modèle « {modele_brut} » n'est plus installé. Choisissez un autre modèle dans la "
        "liste.",
    )


def _resoudre_langue(langue_brute: str) -> tuple[Langue | None, JSONResponse | None]:
    if not langue_brute:
        return None, None
    if langue_brute not in _LANGUES_VALIDES:
        return None, erreur(
            422, "langue_invalide", "Langue non reconnue. Choisissez français ou anglais."
        )
    return langue_brute, None  # type: ignore[return-value]


def _executer_en_fond(
    config: Configuration,
    verrou: VerrouUnique,
    id_lot: str,
    dossier_entree: Path,
    modele: str | None,
    langue: Langue | None,
) -> None:
    try:
        requete = RequeteLot(dossier=dossier_entree, id_lot=id_lot, modele=modele, langue=langue)
        executer_lot(requete, config)
    except Exception:  # noqa: BLE001 - déjà consigné dans journal.jsonl par `executer_lot`
        pass
    finally:
        verrou.liberer()


@routeur.post("/lots")
async def creer_lot(request: Request) -> Response:
    config = _config(request)
    verrou = _verrou(request)
    debut = datetime.now().astimezone()
    # [revue A1/A2] Occupation provisoire, remplacée par `definir` une fois l'id connu.
    if not verrou.prendre(Occupation("fiches", "", None, debut)):
        return _refus_lot_en_cours(verrou.occupation())
    lance = False
    id_lot: str | None = None
    try:
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
        modeles = composition.modeles_installes(config)
        modele_brut = formulaire.get("modele")
        modele, refus_modele = _resoudre_modele(
            modeles, modele_brut if isinstance(modele_brut, str) else ""
        )
        if refus_modele is not None:
            return refus_modele
        langue_brute = formulaire.get("langue")
        langue, refus_langue = _resoudre_langue(
            langue_brute if isinstance(langue_brute, str) else ""
        )
        if refus_langue is not None:
            return refus_langue

        id_lot = nouvel_id_lot(config.chemins.var)
        verrou.definir(Occupation("fiches", id_lot, None, debut))
        dossier_entree = config.chemins.var / "entrees" / id_lot
        dossier_entree.mkdir(parents=True, exist_ok=True)
        for nom, contenu in fichiers:
            (dossier_entree / nom).write_bytes(contenu)
        # [revue A2] lot.json avant le 303 : la page suivante connaît déjà le workflow.
        ecrire_fiche_lot(
            dossier_sorties(config) / id_lot,
            id_lot=id_lot,
            workflow="fiches",
            langue=langue,
            modele_demande=modele,
        )
        _moteur(request).fermer()
        fil = threading.Thread(
            target=_executer_en_fond,
            args=(config, verrou, id_lot, dossier_entree, modele, langue),
            daemon=True,
        )
        fil.start()
        lance = True
        return RedirectResponse(f"/lots/{id_lot}", status_code=303)
    finally:
        if not lance:
            if id_lot is not None:
                _supprimer_dossiers_du_lot(config, id_lot)
            verrou.liberer()


@routeur.get("/lots/{id_lot}/etat")
def etat_lot(request: Request, id_lot: str, depuis: int = Query(0, ge=0)) -> JSONResponse:
    # `depuis` (facultatif) : le JS ne redemande que les nouveaux événements à chaque
    # interrogation, sans recopier tout le journal du lot ; 0 donne la réponse complète.
    etat = lots_app.etat_lot(_config(request), id_lot, _verrou(request).occupation(), depuis)
    if etat is None:
        return erreur(404, "lot_inconnu", "Lot inconnu.")
    return JSONResponse(etat)


@routeur.get("/lots/{id_lot}/rapport.docx")
def rapport_lot(request: Request, id_lot: str) -> Response:
    config = _config(request)
    # [revue A3] `dossier_lot_existant` : aucun GET ne crée de dossier.
    dossier = dossier_lot_existant(id_lot, config)
    if dossier is None:
        return erreur(404, "lot_inconnu", "Lot inconnu.")
    etat = lots_app.etat_lot(config, id_lot, _verrou(request).occupation())
    if etat is None or etat["etat"] != "termine":
        return erreur(409, "lot_non_termine", "Le lot n'est pas terminé.")
    chemin = dossier / RAPPORT
    if not chemin.is_file():
        return erreur(404, "introuvable", "Rapport introuvable.")
    return FileResponse(
        chemin,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=RAPPORT,
    )


def _resume_json(resume: lots_app.ResumeLot) -> dict:
    return {
        "id_lot": resume.id_lot,
        "workflow": resume.workflow,
        "etat": resume.etat,
        "total": resume.total,
        "langue": resume.langue,
        "modele": resume.modele,
        "cree_le": resume.cree_le.isoformat(),
        "url": resume.url,
        "externe": resume.externe,
    }


@routeur.get("/api/lots")
def api_lots(request: Request) -> JSONResponse:
    config = _config(request)
    resumes = lots_app.lister_lots(config, _verrou(request).occupation())
    return JSONResponse({"lots": [_resume_json(resume) for resume in resumes]})


def _modele_json(modele: ModeleInstalle) -> dict:
    return {
        "nom": modele.nom,
        "role": modele.role,
        "taille_o": modele.taille_o,
        "duree_indicative_s": modele.duree_indicative_s,
        "defaut": modele.defaut,
    }


@routeur.get("/api/modeles")
def api_modeles(request: Request) -> JSONResponse:
    config = _config(request)
    modeles = composition.modeles_installes(config)
    return JSONResponse(
        {
            "modeles": [_modele_json(modele) for modele in modeles],
            "langues": ["fr", "en"],
            "langue_defaut": config.fiches.langue,
        }
    )
