"""Routeur du workflow incident dans l'UI (contrats §26, §30, CAP-14).

Même ordre de lancement que `routeurs/lots.creer_lot` (revue W2, consignes pour W4) :
occupation provisoire, validation, `nouvel_id_lot`, `definir`, écriture des journaux, puis
`ecrire_fiche_lot(..., workflow="incident", langue=None)` avant le 303, arrêt du moteur hors de
la boucle d'événements, fil `daemon` qui exécute `executer_incident` et libère le verrou dans un
`finally`. L'état vient de `application/lots.py`, lu sur le disque à chaque appel (§30).
"""

import logging
import re
import shutil
import threading
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException

from waveaudit.application import composition
from waveaudit.application import lots as lots_app
from waveaudit.application.composition import ModeleInstalle
from waveaudit.application.incident import INCIDENT_JSON, RAPPORT_INCIDENT, executer_incident
from waveaudit.application.lot import (
    dossier_lot_existant,
    dossier_sorties,
    ecrire_fiche_lot,
    nouvel_id_lot,
)
from waveaudit.application.moteur_demande import MoteurALaDemande, Occupation, VerrouUnique
from waveaudit.domaine.configuration import Configuration
from waveaudit.domaine.incident import SEVERITES, RapportIncident, RequeteIncident
from waveaudit.interfaces.web.commun import en_mo, erreur, page

_log = logging.getLogger(__name__)

routeur = APIRouter()

MAX_FICHIERS = 50  # contrats §26 [revue A5/E42]
TAILLE_MAX_FICHIER = 10 * 1024 * 1024  # 10 Mio par journal
ANNEE_MIN = 1970
ANNEE_MAX = 2100
_MOTIF_NOM = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]{0,99}$")
_RESERVES_WINDOWS = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)
_LONGUEUR_NOM_AFFICHE = 120


class Refus(Exception):
    """Dépôt refusé : porte la réponse d'erreur codée (§26)."""

    def __init__(self, reponse: JSONResponse) -> None:
        super().__init__()
        self.reponse = reponse


def _nom_affiche(nom_brut: str) -> str:
    return nom_brut[:_LONGUEUR_NOM_AFFICHE]


def _valider_nom(nom_brut: str, deja_vus: set[str]) -> str:
    """Vérifie un nom de journal (contrats §26, §30) ; renvoie le nom retenu.

    Même règle que `routeurs/lots._valider_nom`, sans restriction d'extension (journaux
    `.log`, `.json`, `.csv` ou sans extension comme `auth.log`, `syslog`, `secure`).
    """
    nom = _nom_affiche(nom_brut)
    base = Path(nom_brut).name
    if base != nom_brut or base.endswith((".", " ")) or not _MOTIF_NOM.fullmatch(base):
        raise Refus(
            erreur(
                400,
                "nom_refuse",
                f"Le nom « {nom} » n'est pas accepté. Utilisez des lettres, chiffres, espaces, "
                "points ou tirets.",
            )
        )
    if base.split(".", 1)[0].rstrip(" ").upper() in _RESERVES_WINDOWS:
        raise Refus(
            erreur(
                400,
                "nom_refuse",
                f"Le nom « {nom} » est réservé par Windows. Renommez le fichier.",
            )
        )
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


async def _valider_journaux(fichiers: list[UploadFile]) -> list[tuple[str, bytes]]:
    """Valide et lit chaque journal déposé (§26, §30) ; lève `Refus` au premier refus."""
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
                    f"Ce fichier dépasse 10 Mo ({nom}, {en_mo(taille)}). Réduisez-le ou "
                    "retirez-le du dépôt.",
                    limite="fichier",
                )
            )
        resultat.append((nom, contenu))
    if not any(composition.journal_reconnu(nom) for nom, _ in resultat):
        raise Refus(
            erreur(
                400,
                "aucun_journal_reconnu",
                "Aucun journal reconnu dans le dépôt. Déposez des fichiers Windows "
                "(.json, .csv) ou Linux (auth.log, syslog, secure, .log).",
            )
        )
    return resultat


def _config(request: Request) -> Configuration:
    return request.app.state.config


def _verrou(request: Request) -> VerrouUnique:
    return request.app.state.verrou


def _moteur(request: Request) -> MoteurALaDemande:
    return request.app.state.moteur


def _occupation_json(occupation: Occupation | None) -> dict | None:
    if occupation is None:
        return None
    return {
        "nature": occupation.nature,
        "id_lot": occupation.id_lot,
        "debut": occupation.debut.isoformat(),
    }


def _refus_lot_en_cours(occupation: Occupation | None) -> JSONResponse:
    # [revue W2] L'occupation peut avoir été libérée entre `prendre` et sa lecture.
    debut = occupation.debut.strftime("%H:%M") if occupation is not None else "--:--"
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


def _resoudre_annee(annee_brute: str) -> tuple[int | None, JSONResponse | None]:
    if not annee_brute:
        return datetime.now().year, None
    if not annee_brute.isascii() or not annee_brute.lstrip("-").isdigit():
        return None, erreur(422, "annee_invalide", "Année non reconnue.")
    valeur = int(annee_brute)
    if not (ANNEE_MIN <= valeur <= ANNEE_MAX):
        return None, erreur(
            422,
            "annee_invalide",
            f"Année non reconnue. Choisissez une année entre {ANNEE_MIN} et {ANNEE_MAX}.",
        )
    return valeur, None


def _executer_en_fond(
    config: Configuration,
    verrou: VerrouUnique,
    id_lot: str,
    dossier_entree: Path,
    modele: str | None,
    annee: int,
) -> None:
    try:
        requete = RequeteIncident(dossier=dossier_entree, annee=annee, modele=modele, id_lot=id_lot)
        executer_incident(requete, config)
    except Exception:  # noqa: BLE001 - consigné dans journal.jsonl par `executer_incident` si ouvert
        # [revue W2] Un refus avant le journal (dossier, id déjà exécuté) laisserait sinon le lot
        # « interrompu » sans aucune trace.
        _log.warning("incident %s arrêté", id_lot, exc_info=True)
    finally:
        verrou.liberer()


@routeur.post("/incidents")
async def creer_incident(request: Request) -> Response:
    config = _config(request)
    verrou = _verrou(request)
    debut = datetime.now().astimezone()
    # [revue A1/A2] Occupation provisoire, remplacée par `definir` une fois l'id connu.
    if not verrou.prendre(Occupation("incident", "", None, debut)):
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
        journaux = [v for v in formulaire.getlist("journaux") if isinstance(v, UploadFile)]
        try:
            fichiers = await _valider_journaux(journaux)
        except Refus as refus:
            return refus.reponse
        modeles = composition.modeles_installes(config)
        modele_brut = formulaire.get("modele")
        modele, refus_modele = _resoudre_modele(
            modeles, modele_brut if isinstance(modele_brut, str) else ""
        )
        if refus_modele is not None:
            return refus_modele
        annee_brute = formulaire.get("annee")
        annee, refus_annee = _resoudre_annee(annee_brute if isinstance(annee_brute, str) else "")
        if refus_annee is not None:
            return refus_annee

        id_lot = nouvel_id_lot(config.chemins.var)
        verrou.definir(Occupation("incident", id_lot, None, debut))
        dossier_entree = config.chemins.var / "entrees" / id_lot
        dossier_entree.mkdir(parents=True, exist_ok=True)
        for nom, contenu in fichiers:
            (dossier_entree / nom).write_bytes(contenu)
        # [revue A2] lot.json avant le 303 : la page suivante connaît déjà le workflow.
        ecrire_fiche_lot(
            dossier_sorties(config) / id_lot,
            id_lot=id_lot,
            workflow="incident",
            langue=None,
            modele_demande=modele,
        )
        # [revue W2] Arrêt de llama-server hors de la boucle d'événements.
        await run_in_threadpool(_moteur(request).fermer)
        fil = threading.Thread(
            target=_executer_en_fond,
            args=(config, verrou, id_lot, dossier_entree, modele, annee),
            daemon=True,
        )
        fil.start()
        lance = True
        return RedirectResponse(f"/incidents/{id_lot}", status_code=303)
    finally:
        if not lance:
            if id_lot is not None:
                _supprimer_dossiers_du_lot(config, id_lot)
            verrou.liberer()


@routeur.get("/incidents/{id_lot}", response_class=HTMLResponse, response_model=None)
def page_incident(request: Request, id_lot: str) -> HTMLResponse | Response:
    config = _config(request)
    dossier = dossier_lot_existant(id_lot, config)
    if dossier is None:
        return erreur(404, "lot_inconnu", "Lot inconnu.")
    # §26 : la page d'un lot de fiches redirige vers `/lots/{id}` (l'inverse est posé par W2).
    if lots_app.workflow_lot(dossier) == "fiches":
        return RedirectResponse(f"/lots/{id_lot}", status_code=303)
    return page(request, "incident.html", {"id_lot": id_lot})


@routeur.get("/incidents/{id_lot}/etat")
def etat_incident(request: Request, id_lot: str, depuis: int = Query(0, ge=0)) -> JSONResponse:
    etat = lots_app.etat_lot(_config(request), id_lot, _verrou(request).occupation(), depuis)
    if etat is None:
        return erreur(404, "lot_inconnu", "Lot inconnu.")
    return JSONResponse(etat)


def _lire_rapport(dossier: Path) -> RapportIncident | None:
    try:
        return RapportIncident.model_validate_json(
            (dossier / INCIDENT_JSON).read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        return None


def _par_severite(rapport: RapportIncident) -> dict[str, int]:
    compte = {severite: 0 for severite in SEVERITES}
    for recit in rapport.recits:
        compte[recit.severite] += 1
    return compte


@routeur.get("/incidents/{id_lot}/resultat", response_model=None)
def resultat_incident(request: Request, id_lot: str) -> Response:
    config = _config(request)
    dossier = dossier_lot_existant(id_lot, config)
    if dossier is None:
        return erreur(404, "lot_inconnu", "Lot inconnu.")
    etat = lots_app.etat_lot(config, id_lot, _verrou(request).occupation())
    if etat is None or etat["etat"] != "termine":
        return erreur(409, "lot_non_termine", "Le lot n'est pas terminé.")
    rapport = _lire_rapport(dossier)
    if rapport is None:
        return erreur(404, "introuvable", "Résultat introuvable.")
    return JSONResponse(
        {
            "id_lot": id_lot,
            "rapport": rapport.model_dump(mode="json"),
            "par_severite": _par_severite(rapport),
            "total": len(rapport.recits),
        }
    )


@routeur.get("/incidents/{id_lot}/rapport-incident.docx", response_model=None)
def rapport_incident(request: Request, id_lot: str) -> Response:
    config = _config(request)
    dossier = dossier_lot_existant(id_lot, config)
    if dossier is None:
        return erreur(404, "lot_inconnu", "Lot inconnu.")
    etat = lots_app.etat_lot(config, id_lot, _verrou(request).occupation())
    if etat is None or etat["etat"] != "termine":
        return erreur(409, "lot_non_termine", "Le lot n'est pas terminé.")
    chemin = dossier / RAPPORT_INCIDENT
    if not chemin.is_file():
        return erreur(404, "introuvable", "Rapport introuvable.")
    return FileResponse(
        chemin,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=RAPPORT_INCIDENT,
    )
