"""Service du workflow incident (CERT, contrats §21 « Service », AD-6, AD-8, AD-17).

Lecture, détection, puis récit de chaque détection par le moteur, ouvert seulement s'il y a au
moins une détection. `journal.jsonl` est écrit par `journal.JournalLot` (via l'émetteur du lot,
réutilisé tel quel) avec les `EvenementLot` existants, sans nouveau type.
"""

import shutil
import time
from pathlib import Path

from waveaudit.application import composition
from waveaudit.application.journal import JournalLot
from waveaudit.application.lot import (
    _ID_LOT,
    JOURNAL,
    Abonne,
    _Emetteur,
    _sans_chemin,
    _sorties,
    nouvel_id_lot,
)
from waveaudit.domaine.configuration import Configuration
from waveaudit.domaine.detection import detecter
from waveaudit.domaine.erreurs import EntreeInvalide
from waveaudit.domaine.incident import Recit, RequeteIncident, ResultatIncident
from waveaudit.domaine.modeles import TypeEvenement
from waveaudit.workflows.incident.pipeline import assembler_rapport, traiter_detection

INCIDENT_JSON = "incident.json"
RAPPORT_INCIDENT = "rapport-incident.docx"
WORKFLOW = "incident"


def _id_lot(requete: RequeteIncident, config: Configuration) -> str:
    """Même règle que le lot des fiches : `nouvel_id_lot`, ou identifiant fourni et vérifié."""
    if requete.id_lot is None:
        return nouvel_id_lot(config.chemins.var)
    if not _ID_LOT.fullmatch(requete.id_lot):
        raise EntreeInvalide(f"identifiant de lot invalide : {requete.id_lot!r}")
    dossier = _sorties(config) / requete.id_lot
    try:
        dossier.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    # Nom réservé Windows (NUL…) : mkdir « réussit » sans créer de dossier.
    if not dossier.is_dir():
        raise EntreeInvalide(f"identifiant de lot inutilisable : {requete.id_lot!r}")
    return requete.id_lot


def executer_incident(
    requete: RequeteIncident, config: Configuration, abonne: Abonne | None = None
) -> ResultatIncident:
    """Analyse un dossier de journaux et produit `incident.json` et `rapport-incident.docx`.

    Sortent seulement `EntreeInvalide`, `ConfigurationInvalide`, `MoteurInjoignable` (sonde)
    et `ConnexionInterdite` ; l'échec du moteur pendant un récit donne un repli (AD-6).
    """
    debut = time.perf_counter()
    if not Path(requete.dossier).is_dir():
        raise EntreeInvalide(f"journaux : dossier introuvable ({requete.dossier})")
    id_lot = _id_lot(requete, config)
    dossier_sortie = _sorties(config) / id_lot

    with JournalLot(dossier_sortie / JOURNAL) as journal:
        emetteur = _Emetteur(journal, abonne)
        try:
            ports = composition.creer_ports_incident(config)
            lecture = ports.source_journaux.lire(requete.dossier, annee=requete.annee)
            regles = ports.regles.regles()
            par_id = {regle.id: regle for regle in regles}
            detections = detecter(regles, lecture.evenements)
            emetteur.total = len(detections)
            recits: list[Recit] = []
            if not detections:
                emetteur.emettre(TypeEvenement.LOT_DEMARRE, details={"workflow": WORKFLOW})
            else:
                with composition.ouvrir_moteur_incident(config, requete.modele, id_lot=id_lot) as (
                    moteur,
                    prefixe_systeme,
                    info,
                ):
                    moteur.sonder()
                    emetteur.emettre(
                        TypeEvenement.LOT_DEMARRE,
                        details={"workflow": WORKFLOW, "pid_moteur": info.pid},
                    )
                    for index, detection in enumerate(detections, start=1):
                        emetteur.emettre(
                            TypeEvenement.FICHE_DEMARREE, index=index, note=detection.regle_id
                        )
                        chrono = time.perf_counter()
                        recit = traiter_detection(
                            detection, par_id[detection.regle_id], moteur, prefixe_systeme, config
                        )
                        recits.append(recit)
                        emetteur.emettre(
                            TypeEvenement.FICHE_TERMINEE,
                            index=index,
                            note=detection.regle_id,
                            statut=recit.statut,
                            duree_s=round(time.perf_counter() - chrono, 3),
                        )
            rapport = assembler_rapport(lecture, recits, par_id)
            (dossier_sortie / INCIDENT_JSON).write_bytes(
                rapport.model_dump_json(indent=2).encode("utf-8")
            )
            chemin_rapport = dossier_sortie / RAPPORT_INCIDENT
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
                "workflow": WORKFLOW,
                "detections": len(recits),
                "rapport": RAPPORT_INCIDENT,
            },
        )
    return ResultatIncident(
        id_lot=id_lot,
        dossier_sortie=dossier_sortie,
        rapport=rapport,
        chemin_rapport=chemin_rapport,
        duree_s=duree_lot,
    )
