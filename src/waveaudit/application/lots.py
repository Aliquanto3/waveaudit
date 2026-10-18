"""Fiche d'un lot et liste des lots, lues sur le disque (contrats §30, CAP-9, CAP-10, AD-19).

Remplace le registre en mémoire v0.1.0 (`interfaces/web/routeurs/lots.py`) : la source de
vérité est `journal.jsonl` et `lot.json`, relus à chaque appel. Module de lecture seule, sans
aucune écriture.
"""

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from waveaudit.application import composition
from waveaudit.application.incident import INCIDENT_JSON, RAPPORT_INCIDENT
from waveaudit.application.lot import JOURNAL, dossier_lot_existant, dossier_sorties
from waveaudit.application.moteur_demande import Occupation
from waveaudit.application.relecture import FICHE_LOT, FICHES_V010
from waveaudit.domaine.configuration import Configuration

_log = logging.getLogger(__name__)

Workflow = Literal["fiches", "incident"]
Etat = Literal["termine", "echoue", "en_cours", "interrompu"]
MAX_LOTS = 50


@dataclass(frozen=True)
class ResumeLot:
    """Une ligne de `GET /api/lots` (§30)."""

    id_lot: str
    workflow: Workflow
    etat: Etat
    total: int | None
    langue: str | None
    modele: str | None
    cree_le: datetime
    url: str
    externe: bool  # en cours dans un autre processus (CLI, ou autre instance UI)


def _lire_json(chemin: Path) -> dict | None:
    try:
        return json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _lire_evenements(dossier: Path) -> list[dict]:
    """Chaque ligne de `journal.jsonl` ; une ligne illisible est ignorée (log, §30)."""
    chemin = dossier / JOURNAL
    try:
        texte = chemin.read_text(encoding="utf-8")
    except OSError:
        return []
    evenements: list[dict] = []
    for ligne in texte.splitlines():
        if not ligne.strip():
            continue
        try:
            evenement = json.loads(ligne)
        except ValueError:
            _log.warning("ligne illisible dans %s (ignorée)", chemin)
            continue
        if isinstance(evenement, dict):
            evenements.append(evenement)
    return evenements


def _workflow(dossier: Path, fiche_lot: dict | None) -> Workflow:
    if fiche_lot is not None:
        brut = fiche_lot.get("workflow")
        if brut in ("fiches", "incident"):
            return brut
    if (dossier / INCIDENT_JSON).exists() or (dossier / RAPPORT_INCIDENT).exists():
        return "incident"
    return "fiches"


def _lot_demarre(evenements: list[dict]) -> dict | None:
    for evenement in evenements:
        if evenement.get("type") == "lot_demarre":
            return evenement
    return None


def _fin(evenements: list[dict]) -> tuple[Etat | None, str | None]:
    """`(etat, erreur)` d'après le dernier événement, ou `(None, None)` sans fin."""
    if not evenements:
        return None, None
    dernier = evenements[-1]
    if dernier.get("type") == "lot_termine":
        return "termine", None
    if dernier.get("type") == "lot_echoue":
        message = (dernier.get("details") or {}).get("message")
        return "echoue", message if isinstance(message, str) else None
    return None, None


def _occupe_ce_processus(occupation: Occupation | None, workflow: str, id_lot: str) -> bool:
    return occupation is not None and occupation.nature == workflow and occupation.id_lot == id_lot


def _pid_vivant_externe(config: Configuration, fiche_lot: dict | None) -> bool:
    """[revue A13/E12] `pid` de `lot.json`, différent du processus courant, encore vivant."""
    if fiche_lot is None:
        return False
    pid = fiche_lot.get("pid")
    cree_le_brut = fiche_lot.get("cree_le")
    if not isinstance(pid, int) or pid == os.getpid() or not isinstance(cree_le_brut, str):
        return False
    try:
        cree_le = datetime.fromisoformat(cree_le_brut)
    except ValueError:
        return False
    return composition.processus_actif(pid, cree_le)


def _etat_et_externe(
    config: Configuration,
    id_lot: str,
    workflow: str,
    fiche_lot: dict | None,
    evenements: list[dict],
    occupation: Occupation | None,
) -> tuple[Etat, bool, str | None]:
    etat, erreur = _fin(evenements)
    if etat is not None:
        return etat, False, erreur
    if _occupe_ce_processus(occupation, workflow, id_lot):
        return "en_cours", False, None
    if _pid_vivant_externe(config, fiche_lot):
        return "en_cours", True, None
    return "interrompu", False, None


def _cree_le(dossier: Path, fiche_lot: dict | None, evenements: list[dict]) -> datetime:
    if fiche_lot is not None:
        brut = fiche_lot.get("cree_le")
        if isinstance(brut, str):
            try:
                return datetime.fromisoformat(brut)
            except ValueError:
                pass
    demarre = _lot_demarre(evenements)
    if demarre is not None and isinstance(demarre.get("horodatage"), str):
        try:
            return datetime.fromisoformat(demarre["horodatage"])
        except ValueError:
            pass
    try:
        return datetime.fromtimestamp(dossier.stat().st_mtime).astimezone()
    except OSError:
        return datetime.fromtimestamp(0).astimezone()


def _total_et_modele(
    evenements: list[dict], fiche_lot: dict | None
) -> tuple[int | None, str | None]:
    modele = fiche_lot.get("modele_demande") if fiche_lot else None
    demarre = _lot_demarre(evenements)
    if demarre is None:
        return None, modele
    total = demarre.get("total")
    modele_demarre = (demarre.get("details") or {}).get("modele")
    if isinstance(modele_demarre, str):
        modele = modele_demarre
    return total if isinstance(total, int) else None, modele


def _dossiers_lots(config: Configuration) -> list[Path]:
    racine = dossier_sorties(config)
    if not racine.is_dir():
        return []
    try:
        return [d for d in racine.iterdir() if d.is_dir()]
    except OSError:
        return []


def _resume(
    config: Configuration, dossier: Path, occupation: Occupation | None
) -> ResumeLot | None:
    id_lot = dossier.name
    fiche_lot = _lire_json(dossier / FICHE_LOT)
    evenements = _lire_evenements(dossier)
    v010 = (dossier / FICHES_V010).is_file()
    if fiche_lot is None and not evenements and not v010:
        return None
    workflow = _workflow(dossier, fiche_lot)
    etat, externe, _erreur = _etat_et_externe(
        config, id_lot, workflow, fiche_lot, evenements, occupation
    )
    total, modele = _total_et_modele(evenements, fiche_lot)
    langue = fiche_lot.get("langue") if fiche_lot else None
    url = f"/lots/{id_lot}" if workflow == "fiches" else f"/incidents/{id_lot}"
    return ResumeLot(
        id_lot=id_lot,
        workflow=workflow,
        etat=etat,
        total=total,
        langue=langue if isinstance(langue, str) else None,
        modele=modele,
        cree_le=_cree_le(dossier, fiche_lot, evenements),
        url=url,
        externe=externe,
    )


def lister_lots(config: Configuration, occupation: Occupation | None) -> list[ResumeLot]:
    """Lots récents (§30), triés par `cree_le` puis `id_lot` décroissants, au plus 50."""
    resumes = [
        resume
        for dossier in _dossiers_lots(config)
        if (resume := _resume(config, dossier, occupation)) is not None
    ]
    resumes.sort(key=lambda r: (r.cree_le, r.id_lot), reverse=True)
    return resumes[:MAX_LOTS]


def etat_lot(
    config: Configuration, id_lot: str, occupation: Occupation | None, depuis: int = 0
) -> dict | None:
    """Forme de `GET /lots/{id}/etat` (§30), ou `None` si le lot est inconnu."""
    dossier = dossier_lot_existant(id_lot, config)
    if dossier is None:
        return None
    fiche_lot = _lire_json(dossier / FICHE_LOT)
    evenements = _lire_evenements(dossier)
    workflow = _workflow(dossier, fiche_lot)
    etat, _externe, erreur = _etat_et_externe(
        config, id_lot, workflow, fiche_lot, evenements, occupation
    )
    total, _modele = _total_et_modele(evenements, fiche_lot)
    return {
        "id_lot": id_lot,
        "workflow": workflow,
        "etat": etat,
        "total": total,
        "evenements": evenements[depuis:],
        "erreur": erreur,
    }
