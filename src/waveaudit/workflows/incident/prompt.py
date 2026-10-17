"""Prompt du récit d'une détection (contrats §21 « Prompt et pipeline »)."""

import json

from waveaudit.domaine.incident import Detection, Evenement, Regle
from waveaudit.domaine.ports import Message

LONGUEUR_MAX_PREUVE = 300
_CHAMPS_REGLE = {"id", "titre", "description", "impact", "recommandation"}

CONSIGNE = (
    "Tu es un assistant de rédaction de rapport d'incident de sécurité. Adapte le texte type "
    "de la règle de détection fournie entre les balises <regle> aux preuves fournies entre les "
    "balises <preuves> (une ligne de journal par preuve). Rédige en français les rubriques "
    "titre, recit, impact et recommandation.\n"
    "- Le récit ne relate que des faits présents dans les preuves.\n"
    "- N'invente aucune adresse IP, aucun hachage, aucun compte, aucun hôte ni aucune "
    "technique ATT&CK absents des preuves et de la règle.\n"
    "- Réponds uniquement par un objet JSON conforme au schéma demandé."
)


def ligne_preuve(evenement: Evenement) -> str:
    """`horodatage hote message`, message aux blancs réduits et coupé à 300 caractères."""
    message = " ".join(evenement.message.split())[:LONGUEUR_MAX_PREUVE]
    return f"{evenement.horodatage.isoformat(timespec='seconds')} {evenement.hote} {message}"


def construire(
    regle: Regle, detection: Detection, prefixe_systeme: str, max_preuves: int
) -> list[Message]:
    """Messages `[system, user]` ; au plus `max_preuves` preuves, dans l'ordre de la détection."""
    systeme = f"{prefixe_systeme}\n{CONSIGNE}" if prefixe_systeme else CONSIGNE
    donnees_regle = json.dumps(regle.model_dump(include=_CHAMPS_REGLE), ensure_ascii=False)
    preuves = "\n".join(ligne_preuve(e) for e in detection.evenements[:max_preuves])
    utilisateur = f"<regle>{donnees_regle}</regle>\n<preuves>\n{preuves}\n</preuves>"
    return [
        {"role": "system", "content": systeme},
        {"role": "user", "content": utilisateur},
    ]
