"""Pipeline incident : récit d'une détection, repli, assemblage (contrats §21, AD-6, AD-17).

Aucune entrée-sortie ni aucun événement de lot ici : le service `application.incident` s'en
charge. Le moteur est reçu, jamais instancié.
"""

from collections.abc import Mapping

from waveaudit.domaine.configuration import Configuration
from waveaudit.domaine.erreurs import MoteurInjoignable, SortieInvalide
from waveaudit.domaine.garde_fous_incident import appliquer_recit
from waveaudit.domaine.incident import (
    Detection,
    Evenement,
    LectureJournaux,
    RapportIncident,
    Recit,
    Regle,
    schema_recit,
)
from waveaudit.domaine.indicateurs import extraire
from waveaudit.domaine.modeles import CodeMotif, Motif
from waveaudit.domaine.ports import Message, Moteur
from waveaudit.workflows.incident import prompt


def traiter_detection(
    detection: Detection,
    regle: Regle,
    moteur: Moteur,
    prefixe_systeme: str,
    config: Configuration,
) -> Recit:
    """Indicateurs, récit du moteur puis garde-fous ; repli sur le texte type en cas d'échec.

    `SortieInvalide` : un seul nouvel essai (mêmes messages), puis repli ; `MoteurInjoignable` :
    repli immédiat (AD-6).
    """
    incident = config.incident
    detection = detection.model_copy(update={"indicateurs": extraire(detection.evenements)})
    messages = prompt.construire(regle, detection, prefixe_systeme, incident.max_preuves)
    schema = schema_recit(incident.longueur_max_recit)
    try:
        sortie = _generer_avec_un_essai(
            moteur, messages, schema, incident.max_tokens, config.moteur.seed
        )
        motifs: list[Motif] = []
    except SortieInvalide as erreur:
        sortie = sortie_de_repli(regle)
        motifs = [Motif(code=CodeMotif.REPLI_SORTIE_INVALIDE, detail=str(erreur))]
    except MoteurInjoignable as erreur:
        sortie = sortie_de_repli(regle)
        motifs = [Motif(code=CodeMotif.REPLI_MOTEUR, detail=str(erreur))]
    return appliquer_recit(
        sortie, regle, detection, incident.longueur_max_recit, motifs_initiaux=motifs
    )


def _generer_avec_un_essai(
    moteur: Moteur, messages: list[Message], schema: dict, max_tokens: int, seed: int
) -> dict:
    """`SortieInvalide` : un seul nouvel essai, seed `+ 1` (§5) ; `MoteurInjoignable` remonte."""
    try:
        return moteur.generer_json(messages, schema, max_tokens=max_tokens, seed=seed)
    except SortieInvalide:
        return moteur.generer_json(messages, schema, max_tokens=max_tokens, seed=(seed + 1) % 2**32)


def sortie_de_repli(regle: Regle) -> dict:
    """Rubriques du récit tirées du texte type de la règle, passées ensuite aux garde-fous."""
    return {
        "titre": regle.titre,
        "recit": regle.description,
        "impact": regle.impact,
        "recommandation": regle.recommandation,
    }


def _ordre(evenement: Evenement) -> tuple:
    return (evenement.horodatage, evenement.fichier.casefold(), evenement.ligne)


def assembler_rapport(
    lecture: LectureJournaux, recits: list[Recit], regles: Mapping[str, Regle]
) -> RapportIncident:
    """Rapport d'incident ; `regles` (par id) fournit la recommandation type de chaque règle."""
    detections = [r.detection for r in recits]
    union: dict[tuple[str, int], Evenement] = {}
    for detection in detections:
        for evenement in detection.evenements:
            union.setdefault(evenement.cle, evenement)
    recommandations: list[str] = []
    for detection in detections:
        texte = regles[detection.regle_id].recommandation
        if texte not in recommandations:
            recommandations.append(texte)
    hotes = {hote for detection in detections for hote in detection.hotes}
    return RapportIncident(
        debut=min((d.debut for d in detections), default=None),
        fin=max((d.fin for d in detections), default=None),
        recits=list(recits),
        indicateurs=extraire(sorted(union.values(), key=_ordre)),
        # Double tri : ordre total même pour deux graphies égales en casefold (déterminisme).
        actifs=sorted(sorted(hotes), key=str.casefold),
        recommandations=recommandations,
        sources=dict(lecture.fichiers),
        ignorees=list(lecture.ignorees),
    )
