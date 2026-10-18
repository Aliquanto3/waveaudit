"""Service d'export final et brouillon d'un lot (contrats §27, CAP-13, CAP-17, AD-19).

Appelé par `interfaces/cli.py` (commande `exporter`) et par la future route web `/lots/{id}/export`
(W3a). Aucune commande ni route ne valide de fiche ici : l'export lit `relecture.json` tel quel.
"""

import os
import threading
from pathlib import Path
from typing import Literal

from waveaudit.application import composition, lots
from waveaudit.application.lot import dossier_lot_existant
from waveaudit.application.relecture import charger
from waveaudit.domaine.configuration import Configuration
from waveaudit.domaine.ports import OptionsExport
from waveaudit.domaine.relecture import RefusRelecture, rapport_export

ModeExport = Literal["final", "brouillon"]

# [revue E19] Un verrou par chemin cible résolu : deux exports simultanés sur le même lot et
# le même mode n'écrivent jamais en même temps (même si l'exporteur écrit déjà dans un
# provisoire nommé par uuid avant `os.replace`).
_VERROU_GLOBAL = threading.Lock()
_VERROUS: dict[str, threading.Lock] = {}


def _verrou(chemin: Path) -> threading.Lock:
    cle = os.path.normcase(str(Path(chemin).resolve()))
    with _VERROU_GLOBAL:
        return _VERROUS.setdefault(cle, threading.Lock())


def _nom_fichier(id_lot: str, mode: ModeExport) -> str:
    prefixe = "rapport" if mode == "final" else "brouillon"
    return f"{prefixe}-{id_lot}.docx"


def exporter_lot(config: Configuration, id_lot: str, mode: ModeExport) -> tuple[Path, int]:
    """Exporte le rapport `final` ou `brouillon` du lot `id_lot` (contrats §27).

    Renvoie `(chemin, nombre de fiches non validées)`. `chemin` = `var/sorties/<id>/rapport-
    <id>.docx` ou `brouillon-<id>.docx`, écrasé à chaque export. Lève `RefusRelecture` :
    `lot_inconnu` (lot absent de `dossier_sorties`), `lot_incident` (lot du workflow incident),
    `lot_en_cours` (verrou de ce processus, ou pid vivant d'un autre processus sans fin, §30),
    `aucune_fiche_validee` (mode `final` sans fiche validée).
    """
    dossier = dossier_lot_existant(id_lot, config)
    if dossier is None:
        raise RefusRelecture("lot_inconnu", "Ce lot est inconnu.")
    resume = lots.etat_lot(config, id_lot, None)
    if resume is None:
        raise RefusRelecture("lot_inconnu", "Ce lot est inconnu.")
    if resume["workflow"] == "incident":
        raise RefusRelecture("lot_incident", "Ce lot est un lot incident, sans fiches à exporter.")
    if resume["etat"] == "en_cours":
        raise RefusRelecture("lot_en_cours", "Ce lot est en cours de traitement.")
    etat = charger(dossier)
    rapport, non_validees = rapport_export(etat, mode)
    if mode == "final" and not rapport.fiches:
        raise RefusRelecture("aucune_fiche_validee", "Aucune fiche n'est validée dans ce lot.")
    chemin = dossier / _nom_fichier(id_lot, mode)
    options = OptionsExport(langue=etat.langue, mode=mode, non_validees=non_validees)
    with _verrou(chemin):
        composition.creer_exporteur(config).exporter(rapport, chemin, options)
    return chemin, len(non_validees)
