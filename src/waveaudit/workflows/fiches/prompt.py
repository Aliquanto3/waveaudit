"""Construction du prompt d'adaptation d'un constat type (contrats §8, AD-4)."""

import json
import re

from waveaudit.domaine.modeles import ConstatType, Note
from waveaudit.domaine.ports import Message

MARQUE_TRONCATURE = "[…tronqué]"

# [revue Q1] motif du §8, blancs étendus aux caractères de format invisibles (U+200B, etc.).
_BLANCS = r"[\s­᠎​-‏‪-‮⁠-⁤﻿]*"
_BALISE = re.compile(rf"<(?={_BLANCS}/?{_BLANCS}(?:note|constat)\b)", re.IGNORECASE)


def echapper(texte: str) -> str:
    """[v2] CAP-2 : neutralise les balises `note`/`constat` dans un texte (§8), même longueur."""
    return _BALISE.sub("‹", texte)  # U+2039


CONSIGNE = (
    "Tu es un assistant de rédaction d'audit de sécurité. Adapte le constat type fourni entre "
    "les balises <constat> aux observations de la note d'audit fournie entre les balises "
    "<note>. Rédige en français les rubriques titre, description, impact et recommandation.\n"
    "- N'invente aucun identifiant, aucune référence, aucune URL ni aucun fait absent de la "
    "note.\n"
    "- Garde le vecteur CVSS par défaut du constat type, sauf si la note le contredit.\n"
    "- Réponds uniquement par un objet JSON conforme au schéma demandé."
)

_CHAMPS_CONSTAT = {"id", "titre", "description", "impact", "recommandation", "cvss_vecteur"}


def tronquer(corps: str, taille_max_note: int) -> tuple[str, bool]:
    """Corps limité à `taille_max_note` caractères, et vrai s'il a été tronqué."""
    if len(corps) <= taille_max_note:
        return corps, False
    return corps[:taille_max_note] + MARQUE_TRONCATURE, True


def construire(
    note: Note, constat: ConstatType, prefixe_systeme: str, taille_max_note: int
) -> list[Message]:
    """Messages `[system, user]` ; `constat_attendu` et les références n'y figurent jamais."""
    systeme = f"{prefixe_systeme}\n{CONSIGNE}" if prefixe_systeme else CONSIGNE
    donnees_constat = json.dumps(constat.model_dump(include=_CHAMPS_CONSTAT), ensure_ascii=False)
    corps, _ = tronquer(echapper(note.corps), taille_max_note)
    actif = f"Actif : {echapper(note.actif)}\n" if note.actif else ""
    utilisateur = f"<constat>{donnees_constat}</constat>\n<note>{actif}{corps}</note>"
    return [
        {"role": "system", "content": systeme},
        {"role": "user", "content": utilisateur},
    ]
