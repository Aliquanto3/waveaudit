"""Routeur de la relecture d'un lot (contrats §24 à §27, §26 « Routes », CAP-10 à CAP-13).

Routes JSON : liste et détail des entrées, catalogue, correction, validation, changement de
candidat (régénération sous le `VerrouUnique`) et export final ou brouillon. L'état vient de
`application/relecture.py` (seul écrivain de `relecture.json`) et de `application/lots.py`
(état du lot). Aucun GET n'écrit : la génération interrompue est calculée à la lecture.
Les règles communes (Host, Origin, CSRF, taille, en-têtes) sont posées par `app.py`.
"""

import json
import logging
import threading
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr, ValidationError

from waveaudit.application import composition, relecture
from waveaudit.application import lots as lots_app
from waveaudit.application.export import exporter_lot
from waveaudit.application.lot import dossier_lot_existant
from waveaudit.application.moteur_demande import MoteurALaDemande, Occupation, VerrouUnique
from waveaudit.domaine.configuration import Configuration
from waveaudit.domaine.modeles import ConstatType, Langue, Reference, Statut
from waveaudit.domaine.relecture import (
    EntreeRelecture,
    EtatRelecture,
    FicheCorrigee,
    RefusRelecture,
    corriger,
    fiche_courante,
    valider,
)
from waveaudit.interfaces.web.commun import erreur

_log = logging.getLogger(__name__)

routeur = APIRouter()

TYPE_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

# Statut HTTP de chaque code de refus du domaine ou des services (§26, table des routes).
_STATUTS = {
    "lot_inconnu": 404,
    "lot_incident": 404,
    "entree_inconnue": 404,
    "conflit_version": 409,
    "generation_en_cours": 409,
    "confirmation_requise": 409,
    "lot_en_cours": 409,
    "aucune_fiche_validee": 409,
}  # tout autre code (règles de corriger, valider, demarrer_regeneration) : 422

MSG_EXTERNE = (
    "Ce lot est en cours dans un autre programme (CLI). Attendez sa fin pour le modifier ou "
    "l'exporter."
)
MSG_ILLISIBLE = (
    "L'état de relecture de ce lot (relecture.json) est illisible ; il n'a pas été modifié."
)
MSG_ECRITURE = (
    "Enregistrement impossible : le fichier du lot est verrouillé par un autre programme. "
    "Réessayez dans un instant."
)
MSG_EXPORT_VERROUILLE = (
    "Le rapport est ouvert dans un autre programme (Word ?). Fermez-le, puis exportez à nouveau."
)


class _Refus(Exception):
    """Réponse d'erreur codée prête (§26), levée par les étapes communes."""

    def __init__(self, reponse: JSONResponse) -> None:
        super().__init__()
        self.reponse = reponse


# --- Corps des écritures ---------------------------------------------------------------------


class _Corps(BaseModel):
    model_config = ConfigDict(extra="ignore")


class CorpsCorrection(_Corps):
    version: StrictInt
    titre: StrictStr
    description: StrictStr
    impact: StrictStr
    recommandation: StrictStr
    cvss_vecteur: StrictStr = Field(max_length=100)  # borne de FicheCorrigee
    references: list[StrictStr]


class CorpsValidation(_Corps):
    version: StrictInt


class CorpsCandidat(_Corps):
    version: StrictInt
    constat_id: StrictStr
    confirmer: StrictBool = False


async def _corps(request: Request, modele: type[_Corps]) -> Any:
    try:
        return modele.model_validate(json.loads(await request.body()))
    except (ValueError, ValidationError):
        raise _Refus(erreur(422, "corps_invalide", "Corps de requête invalide.")) from None


# --- Étapes communes -------------------------------------------------------------------------


def _config(request: Request) -> Configuration:
    return request.app.state.config


def _occupation(request: Request) -> Occupation | None:
    return request.app.state.verrou.occupation()


def _refus_code(exc: RefusRelecture, **champs: Any) -> JSONResponse:
    return erreur(_STATUTS.get(exc.code, 422), exc.code, exc.message, **champs)


def _dossier(config: Configuration, id_lot: str) -> Path:
    # [revue A3] `dossier_lot_existant` : aucun GET ne crée de dossier.
    dossier = dossier_lot_existant(id_lot, config)
    if dossier is None:
        raise _Refus(erreur(404, "lot_inconnu", "Lot inconnu."))
    return dossier


def _charger(dossier: Path, occupation: Occupation | None) -> EtatRelecture:
    """`relecture.charger`, refus codés : lot sans relecture (incident) → 404, illisible → 409."""
    try:
        return relecture.charger(dossier, occupation=occupation)
    except RefusRelecture as exc:
        raise _Refus(_refus_code(exc)) from None
    except ValueError:
        # [arbitrage R2] Fichier corrompu (ValidationError) : erreur codée, jamais un 500 brut.
        _log.warning("relecture illisible pour %s", dossier.name, exc_info=True)
        raise _Refus(erreur(409, "relecture_illisible", MSG_ILLISIBLE)) from None


def _entree(etat: EtatRelecture, index: int) -> EntreeRelecture:
    # [revue E21] index hors de 1..n → 404.
    if 1 <= index <= len(etat.entrees):
        for entree in etat.entrees:
            if entree.index == index:
                return entree
    raise _Refus(erreur(404, "entree_inconnue", "Cette entrée n'existe pas dans le lot."))


def _en_cours_externe(config: Configuration, id_lot: str, occupation: Occupation | None) -> bool:
    """[revue A13/E12] Lot `en_cours` d'après `lots.etat_lot` sans que ce processus le porte."""
    if occupation is not None and occupation.id_lot == id_lot:
        return False
    etat = lots_app.etat_lot(config, id_lot, occupation)
    return etat is not None and etat["etat"] == "en_cours"


def _refuser_si_externe(config: Configuration, id_lot: str, occupation: Occupation | None) -> None:
    if _en_cours_externe(config, id_lot, occupation):
        raise _Refus(erreur(409, "lot_en_cours_externe", MSG_EXTERNE))


def _occupation_json(occupation: Occupation | None) -> dict | None:
    if occupation is None:
        return None
    return {
        "nature": occupation.nature,
        "id_lot": occupation.id_lot,
        "index": occupation.index,
        "debut": occupation.debut.isoformat(),
    }


def _refus_lot_en_cours(occupation: Occupation | None) -> JSONResponse:
    # L'occupation peut avoir été libérée entre `prendre` et sa lecture.
    debut = occupation.debut.strftime("%H:%M") if occupation is not None else "--:--"
    return erreur(
        409,
        "lot_en_cours",
        f"Un lot est déjà en cours (lancé à {debut}). Attendez sa fin ou reprenez-le.",
        occupation=_occupation_json(occupation),
    )


def _executer(fonction: Callable[[], Response]) -> Response:
    try:
        return fonction()
    except _Refus as refus:
        return refus.reponse


# --- Présentation ----------------------------------------------------------------------------


def _catalogue(config: Configuration) -> dict[str, ConstatType]:
    return {constat.id: constat for constat in composition.creer_catalogue(config).constats()}


def _titre(constat: ConstatType | None, langue: Langue, defaut: str) -> str:
    if constat is None:
        return defaut
    try:
        return constat.textes(langue).titre
    except ValueError:
        return constat.titre


def _statut_generation(e: EntreeRelecture) -> str | None:
    if e.fiche_generee is not None:
        return str(e.fiche_generee.statut)
    if e.ecartee is not None:
        return str(e.ecartee.statut)
    return None


def _resume_entree(e: EntreeRelecture) -> dict:
    return {
        "index": e.index,
        "note": e.note,
        "etat": e.etat,
        "statut_generation": _statut_generation(e),
        "statut_relecture": e.statut_relecture,
        "generation": e.generation,
        "version": e.version,
        "titre": fiche_courante(e).titre if e.etat == "fiche" else None,
    }


def _entree_json(e: EntreeRelecture) -> dict:
    return e.model_dump(mode="json")


def _modele_regeneration(config: Configuration, etat: EtatRelecture) -> str | None:
    """Modèle résolu du lot [revue A15/A16] ; `None` : modèle par défaut (externe)."""
    if config.moteur.mode == "externe":
        return etat.modele_demande
    return etat.modele or None


def _modele_disponible(config: Configuration, etat: EtatRelecture) -> bool:
    """§24 : en local-gere, le modèle du lot doit figurer dans `modeles_installes`."""
    if config.moteur.mode == "externe":
        return True
    noms = {modele.nom for modele in composition.modeles_installes(config)}
    return _modele_regeneration(config, etat) in noms


def _regenerable(e: EntreeRelecture) -> bool:
    """Entrée qu'un changement de candidat peut régénérer (règles de `demarrer_regeneration`)."""
    non_rattachee = e.ecartee is not None and e.ecartee.statut == Statut.NON_RATTACHEE
    return (
        (e.etat == "fiche" or (e.etat == "ecartee" and non_rattachee))
        and e.source is not None
        and e.generation != "en_cours"
    )


# --- Lectures --------------------------------------------------------------------------------


@routeur.get("/lots/{id_lot}/relecture")
def lire_relecture(request: Request, id_lot: str) -> Response:
    def traiter() -> Response:
        config = _config(request)
        occupation = _occupation(request)
        dossier = _dossier(config, id_lot)
        etat = _charger(dossier, occupation)
        etat_lot = lots_app.etat_lot(config, id_lot, occupation)
        non_validees = sum(
            1 for e in etat.entrees if e.etat == "fiche" and e.statut_relecture == "a_valider"
        )
        return JSONResponse(
            {
                "id_lot": etat.id_lot,
                "langue": etat.langue,
                "modele": etat.modele,
                "etat_lot": etat_lot["etat"] if etat_lot is not None else None,
                "non_validees": non_validees,
                "entrees": [_resume_entree(e) for e in etat.entrees],
            }
        )

    return _executer(traiter)


@routeur.get("/lots/{id_lot}/entrees/{index}")
def lire_entree(request: Request, id_lot: str, index: int) -> Response:
    def traiter() -> Response:
        config = _config(request)
        occupation = _occupation(request)
        dossier = _dossier(config, id_lot)
        etat = _charger(dossier, occupation)
        e = _entree(etat, index)
        externe = _en_cours_externe(config, id_lot, occupation)
        catalogue = _catalogue(config)
        candidats = [
            {
                "id": c.id,
                "score": c.score,
                "titre": _titre(catalogue.get(c.id), etat.langue, c.id),
            }
            for c in e.candidats
        ]
        generable = _regenerable(e) and not externe and _modele_disponible(config, etat)
        modifiable = e.etat == "fiche" and e.generation != "en_cours" and not externe
        return JSONResponse(
            {
                "entree": _entree_json(e),
                "fiche_courante": (
                    fiche_courante(e).model_dump(mode="json") if e.etat == "fiche" else None
                ),
                "candidats_detail": candidats,
                "generable": generable,
                "modifiable": modifiable,
            }
        )

    return _executer(traiter)


@routeur.get("/lots/{id_lot}/catalogue")
def lire_catalogue(request: Request, id_lot: str) -> Response:
    def traiter() -> Response:
        config = _config(request)
        etat = _charger(_dossier(config, id_lot), _occupation(request))
        constats = sorted(_catalogue(config).values(), key=lambda c: c.id)
        return JSONResponse(
            {
                "constats": [
                    {"id": c.id, "famille": c.famille, "titre": _titre(c, etat.langue, c.id)}
                    for c in constats
                ]
            }
        )

    return _executer(traiter)


# --- Écritures -------------------------------------------------------------------------------


def _preparer_ecriture(
    request: Request, id_lot: str, index: int
) -> tuple[Configuration, Path, EtatRelecture, Occupation | None]:
    """404 (lot, entrée), 409 `relecture_illisible`, 409 `lot_en_cours_externe`."""
    config = _config(request)
    occupation = _occupation(request)
    dossier = _dossier(config, id_lot)
    etat = _charger(dossier, occupation)
    _entree(etat, index)
    _refuser_si_externe(config, id_lot, occupation)
    return config, dossier, etat, occupation


def _modifier(
    dossier: Path,
    index: int,
    version: int,
    operation: relecture.Operation,
    occupation: Occupation | None,
) -> Response:
    try:
        entree = relecture.modifier(dossier, index, version, operation, occupation=occupation)
    except RefusRelecture as exc:
        if exc.code == "conflit_version":
            actuelle = _entree(_charger(dossier, occupation), index)
            return _refus_code(exc, entree=_entree_json(actuelle))
        return _refus_code(exc)
    except OSError:
        # [revue A11/E15] PermissionError survivant aux réessais du §25 : rien n'a changé.
        _log.warning("écriture de relecture impossible (%s)", dossier.name, exc_info=True)
        return erreur(503, "ecriture_impossible", MSG_ECRITURE)
    except ValueError:
        _log.warning("relecture illisible pour %s", dossier.name, exc_info=True)
        return erreur(409, "relecture_illisible", MSG_ILLISIBLE)
    return JSONResponse({"entree": _entree_json(entree)})


def _operation_correction(corps: CorpsCorrection, longueur_max: int) -> relecture.Operation:
    def operation(e: EntreeRelecture) -> EntreeRelecture:
        generees = {r.id: r for r in (e.fiche_generee.references if e.fiche_generee else [])}
        # Un id inconnu garde une référence de façade : `corriger` le refuse
        # (`reference_ajoutee`) dans l'ordre de ses refus.
        references = [generees.get(i) or Reference(id=i, titre=i, url="") for i in corps.references]
        correction = FicheCorrigee(
            titre=corps.titre,
            description=corps.description,
            impact=corps.impact,
            recommandation=corps.recommandation,
            cvss_vecteur=corps.cvss_vecteur,
            cvss=None,  # recalculé par `corriger` (domaine/cvss31), jamais repris du client
            references=references,
        )
        return corriger(e, correction, longueur_max)

    return operation


@routeur.put("/lots/{id_lot}/entrees/{index}/correction")
async def corriger_entree(request: Request, id_lot: str, index: int) -> Response:
    try:
        corps: CorpsCorrection = await _corps(request, CorpsCorrection)
    except _Refus as refus:
        return refus.reponse

    def traiter() -> Response:
        config, dossier, _etat, occupation = _preparer_ecriture(request, id_lot, index)
        operation = _operation_correction(corps, config.moteur.longueur_max_rubrique)
        return _modifier(dossier, index, corps.version, operation, occupation)

    return await run_in_threadpool(_executer, traiter)


@routeur.post("/lots/{id_lot}/entrees/{index}/validation")
async def valider_entree(request: Request, id_lot: str, index: int) -> Response:
    try:
        corps: CorpsValidation = await _corps(request, CorpsValidation)
    except _Refus as refus:
        return refus.reponse

    def traiter() -> Response:
        _config_, dossier, _etat, occupation = _preparer_ecriture(request, id_lot, index)
        return _modifier(dossier, index, corps.version, valider, occupation)

    return await run_in_threadpool(_executer, traiter)


def _regenerer_en_fond(
    config: Configuration,
    dossier: Path,
    index: int,
    constat_id: str,
    verrou: VerrouUnique,
    moteur: MoteurALaDemande,
) -> None:
    try:
        relecture.regenerer(config, dossier, index, constat_id, moteur)
    except Exception:  # noqa: BLE001 - `regenerer` consigne déjà tout échec dans l'entrée
        _log.exception("régénération de l'entrée %s arrêtée", index)
    finally:
        verrou.liberer()


@routeur.post("/lots/{id_lot}/entrees/{index}/candidat")
async def changer_candidat(request: Request, id_lot: str, index: int) -> Response:
    try:
        corps: CorpsCandidat = await _corps(request, CorpsCandidat)
    except _Refus as refus:
        return refus.reponse

    def traiter() -> Response:
        config, dossier, etat, _occupation_ = _preparer_ecriture(request, id_lot, index)
        e = _entree(etat, index)
        if e.source is not None and not _modele_disponible(config, etat):
            # §24 : refus avant tout démarrage, rien n'est écrit.
            nom = _modele_regeneration(config, etat) or etat.modele
            return erreur(
                422,
                "modele_indisponible",
                f"Le modèle « {nom} » n'est plus installé. Choisissez un autre modèle dans la "
                "liste.",
            )
        ids_catalogue = tuple(_catalogue(config))
        verrou = request.app.state.verrou
        # §26 : le verrou d'abord ; une régénération en cours donne donc 409 `lot_en_cours`.
        if not verrou.prendre(
            Occupation("regeneration", id_lot, index, datetime.now().astimezone())
        ):
            return _refus_lot_en_cours(verrou.occupation())
        lance = False
        try:
            try:
                entree = relecture.demarrer_regeneration(
                    dossier,
                    index,
                    corps.version,
                    corps.constat_id,
                    corps.confirmer,
                    ids_catalogue=ids_catalogue,
                )
            except RefusRelecture as exc:
                if exc.code == "conflit_version":
                    actuelle = _entree(_charger(dossier, None), index)
                    return _refus_code(exc, entree=_entree_json(actuelle))
                return _refus_code(exc)
            except OSError:
                _log.warning("écriture de relecture impossible (%s)", dossier.name, exc_info=True)
                return erreur(503, "ecriture_impossible", MSG_ECRITURE)
            except ValueError:
                return erreur(409, "relecture_illisible", MSG_ILLISIBLE)
            fil = threading.Thread(
                target=_regenerer_en_fond,
                args=(config, dossier, index, corps.constat_id, verrou, request.app.state.moteur),
                daemon=True,
            )
            fil.start()
            lance = True
            return JSONResponse({"entree": _entree_json(entree)}, status_code=202)
        finally:
            if not lance:
                verrou.liberer()

    return await run_in_threadpool(_executer, traiter)


@routeur.post("/lots/{id_lot}/export")
async def exporter(request: Request, id_lot: str) -> Response:
    """[revue A4/E26] Export en POST seulement : aucun GET n'écrit de fichier."""
    try:
        mode = json.loads(await request.body()).get("type")
    except (ValueError, AttributeError):
        mode = None
    if mode not in ("final", "brouillon"):
        return erreur(422, "type_invalide", "Type d'export inconnu : « final » ou « brouillon ».")

    def traiter() -> Response:
        config = _config(request)
        occupation = _occupation(request)
        _dossier(config, id_lot)
        try:
            chemin, non_validees = exporter_lot(config, id_lot, mode, occupation=occupation)
        except RefusRelecture as exc:
            if exc.code == "lot_en_cours" and (occupation is None or occupation.id_lot != id_lot):
                return erreur(409, "lot_en_cours_externe", MSG_EXTERNE)
            return _refus_code(exc)
        except PermissionError:
            return erreur(409, "export_verrouille", MSG_EXPORT_VERROUILLE)
        except ValueError:
            _log.warning("relecture illisible pour %s", id_lot, exc_info=True)
            return erreur(409, "relecture_illisible", MSG_ILLISIBLE)
        # Lu en mémoire : aucun descripteur ouvert ne bloque l'export suivant (os.replace).
        en_tetes = {"Content-Disposition": f'attachment; filename="{chemin.name}"'}
        if mode == "final":
            en_tetes["X-Non-Validees"] = str(non_validees)
        return Response(chemin.read_bytes(), media_type=TYPE_DOCX, headers=en_tetes)

    return await run_in_threadpool(_executer, traiter)
