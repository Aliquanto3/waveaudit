"""Service de lot unique pour la CLI et l'UI (contrats §9, AD-2, AD-6, AD-8).

Émet les `EvenementLot` des fiches ; `journal.jsonl` est écrit par `journal.JournalLot`
(seul écrivain), avant l'appel de l'abonné.
"""

import json
import logging
import re
import shutil
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from waveaudit.application import composition
from waveaudit.application.journal import JournalLot
from waveaudit.domaine.configuration import Configuration
from waveaudit.domaine.erreurs import EntreeInvalide
from waveaudit.domaine.modeles import (
    EvenementLot,
    Fiche,
    RequeteLot,
    ResultatElement,
    ResultatLot,
    Statut,
    TypeEvenement,
)
from waveaudit.workflows.registre import REGISTRE

_log = logging.getLogger(__name__)

Abonne = Callable[[EvenementLot], None]
FICHES = "fiches.json"
JOURNAL = "journal.jsonl"
RAPPORT = "rapport.docx"
_ID_LOT = re.compile(r"[0-9A-Za-z][0-9A-Za-z-]*")
# Chemin absolu Windows (C:\..., \\serveur\...) ou POSIX (/a/b) dans un message d'erreur.
# Un espace reste dans le chemin si le mot suivant contient encore un séparateur
# (« C:\Users\Prénom Nom\x.md absent ») ; un chemin entre apostrophes est pris en entier.
_CAR = r"[^\s'\"()<>,;]"
_DEBUT = r"(?:(?<!\w)[A-Za-z]:[\\/]|\\\\|(?<![\w/:.])/(?=[^\s/]+/))"
_CHEMIN_ABSOLU = re.compile(
    rf"(?<=')(?:(?<!\w)[A-Za-z]:[\\/]|\\\\|/)[^'\n]*(?=')|{_DEBUT}(?:{_CAR}| (?={_CAR}*[\\/]))*"
)


def _sans_chemin(message: str) -> str:
    """Remplace chaque chemin absolu par son nom de fichier (AD-8 : jamais de chemin absolu)."""
    return _CHEMIN_ABSOLU.sub(lambda m: Path(m.group().rstrip(".:")).name or "…", message)


def _maintenant() -> datetime:
    return datetime.now().astimezone()


def _sorties(config: Configuration) -> Path:
    return config.chemins.var / "sorties"


def nouvel_id_lot(var: Path) -> str:
    """`AAAAMMJJ-HHMMSS`, suffixé `-2`, `-3`… ; crée `var/sorties/<id>/` sans écraser."""
    sorties = var / "sorties"
    sorties.mkdir(parents=True, exist_ok=True)
    base = _maintenant().strftime("%Y%m%d-%H%M%S")
    rang = 1
    while True:
        candidat = base if rang == 1 else f"{base}-{rang}"
        try:
            (sorties / candidat).mkdir(exist_ok=False)
        except FileExistsError:
            rang += 1
            continue
        return candidat


class _Emetteur:
    """Écrit chaque événement dans `journal.jsonl` (une ligne, flush), puis appelle l'abonné."""

    def __init__(self, journal: JournalLot, abonne: Abonne | None) -> None:
        self._journal = journal
        self._abonne = abonne
        self.total = 0

    def emettre(
        self,
        type_: TypeEvenement,
        *,
        index: int | None = None,
        note: str | None = None,
        statut: Statut | None = None,
        duree_s: float | None = None,
        details: dict[str, str | int | float | None] | None = None,
    ) -> None:
        evenement = EvenementLot(
            type=type_,
            horodatage=_maintenant(),
            index=index,
            total=self.total,
            note=note,
            statut=statut,
            duree_s=duree_s,
            details=details or {},
        )
        self._journal.ecrire(evenement)
        if self._abonne is not None:
            try:
                self._abonne(evenement)
            except Exception:
                _log.exception("abonné du lot en erreur sur %s (ignoré)", type_)


def _type_fin(resultat: ResultatElement) -> TypeEvenement:
    if isinstance(resultat, Fiche):
        return TypeEvenement.FICHE_TERMINEE
    if resultat.statut == Statut.NON_RATTACHEE:
        return TypeEvenement.FICHE_NON_RATTACHEE
    return TypeEvenement.FICHE_NON_TRAITEE


def executer_lot(
    requete: RequeteLot, config: Configuration, abonne: Abonne | None = None
) -> ResultatLot:
    """Exécute un lot complet ; renvoie le résultat ou lève une erreur d'arrêt du lot (AD-6)."""
    debut = time.perf_counter()
    if requete.workflow not in REGISTRE:
        raise EntreeInvalide(f"workflow inconnu : {requete.workflow}")
    if not Path(requete.dossier).is_dir():
        raise EntreeInvalide(f"notes : dossier introuvable ({requete.dossier})")
    if requete.id_lot is None:
        id_lot = nouvel_id_lot(config.chemins.var)
    else:
        if not _ID_LOT.fullmatch(requete.id_lot):
            raise EntreeInvalide(f"identifiant de lot invalide : {requete.id_lot!r}")
        id_lot = requete.id_lot
        try:
            (_sorties(config) / id_lot).mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        # Nom réservé Windows (NUL…) : mkdir « réussit » sans créer de dossier.
        if not (_sorties(config) / id_lot).is_dir():
            raise EntreeInvalide(f"identifiant de lot inutilisable : {id_lot!r}")
    dossier_sortie = _sorties(config) / id_lot

    with JournalLot(dossier_sortie / JOURNAL) as journal:
        emetteur = _Emetteur(journal, abonne)
        try:
            with composition.ouvrir(config, requete.modele, id_lot=id_lot) as (ports, info):
                ports.moteur.sonder()
                workflow = REGISTRE[requete.workflow](config, ports)
                elements = sorted(
                    workflow.preparer(requete.dossier), key=lambda e: e.fichier.casefold()
                )
                emetteur.total = len(elements)
                emetteur.emettre(
                    TypeEvenement.LOT_DEMARRE,
                    details={"id_lot": id_lot, "modele": info.nom_modele, "pid_moteur": info.pid},
                )
                resultats: list[ResultatElement] = []
                for index, element in enumerate(elements, start=1):
                    emetteur.emettre(
                        TypeEvenement.FICHE_DEMARREE, index=index, note=element.fichier
                    )
                    chrono = time.perf_counter()
                    resultat = workflow.traiter(element)
                    duree = round(time.perf_counter() - chrono, 3)
                    resultats.append(resultat)
                    emetteur.emettre(
                        _type_fin(resultat),
                        index=index,
                        note=element.fichier,
                        statut=resultat.statut,
                        duree_s=duree,
                    )
                rapport = workflow.assembler(resultats)
                (dossier_sortie / FICHES).write_text(
                    json.dumps(rapport.model_dump(mode="json"), ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                chemin_rapport = dossier_sortie / RAPPORT
                ports.exporteur.exporter(rapport, chemin_rapport)
                if requete.copie_rapport is not None:
                    shutil.copyfile(chemin_rapport, requete.copie_rapport)
        except BaseException as erreur:
            emetteur.emettre(
                TypeEvenement.LOT_ECHOUE,
                details={"erreur": type(erreur).__name__, "message": _sans_chemin(str(erreur))},
            )
            raise
        duree_lot = round(time.perf_counter() - debut, 3)
        emetteur.emettre(
            TypeEvenement.LOT_TERMINE,
            duree_s=duree_lot,
            details={
                "id_lot": id_lot,
                "fiches": len(rapport.fiches),
                "ecartees": len(rapport.ecartees),
                "rapport": RAPPORT,
            },
        )
    return ResultatLot(
        id_lot=id_lot,
        dossier_sortie=dossier_sortie,
        rapport=rapport,
        chemin_rapport=chemin_rapport,
        duree_s=duree_lot,
    )
