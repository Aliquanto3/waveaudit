"""Construction du prompt d'adaptation d'un constat type (contrats §8, AD-4)."""

import json
import re

from waveaudit.domaine.modeles import ConstatType, Langue, Note
from waveaudit.domaine.ports import Message

MARQUE_TRONCATURE = "[…tronqué]"

# [revue Q1] motif du §8, blancs étendus aux caractères de format invisibles (U+200B, etc.).
_BLANCS = r"[\s­᠎​-‏‪-‮⁠-⁤﻿]*"
_BALISE = re.compile(rf"<(?={_BLANCS}/?{_BLANCS}(?:note|constat)\b)", re.IGNORECASE)


def echapper(texte: str) -> str:
    """[v2] CAP-2 : neutralise les balises `note`/`constat` dans un texte (§8), même longueur."""
    return _BALISE.sub("‹", texte)  # U+2039


# [v2] CAP-8 : une consigne par langue (contrats §8, §23). `CONSIGNE` reste exporté (= fr).
CONSIGNES: dict[Langue, str] = {
    "fr": (
        "Tu es un assistant de rédaction d'audit de sécurité. Adapte le constat type fourni "
        "entre les balises <constat> aux observations de la note d'audit fournie entre les "
        "balises <note>. Rédige en français les rubriques titre, description, impact et "
        "recommandation.\n"
        "- N'invente aucun identifiant, aucune référence, aucune URL ni aucun fait absent de la "
        "note.\n"
        "- Garde le vecteur CVSS par défaut du constat type, sauf si la note le contredit.\n"
        "- Réponds uniquement par un objet JSON conforme au schéma demandé."
    ),
    "en": (
        "You are a security audit writing assistant. Adapt the constat type given between the "
        "<constat> tags to the observations of the audit note given between the <note> tags. "
        "Write the titre, description, impact and recommandation sections in English.\n"
        "- Do not invent any identifier, reference, URL or fact absent from the note.\n"
        "- Keep the constat type's default CVSS vector, unless the note contradicts it.\n"
        "- Reply only with a JSON object conforming to the requested schema."
    ),
}
CONSIGNE = CONSIGNES["fr"]

_LIBELLE_ACTIF: dict[Langue, str] = {"fr": "Actif : ", "en": "Asset: "}


def tronquer(corps: str, taille_max_note: int) -> tuple[str, bool]:
    """Corps limité à `taille_max_note` caractères, et vrai s'il a été tronqué."""
    if len(corps) <= taille_max_note:
        return corps, False
    return corps[:taille_max_note] + MARQUE_TRONCATURE, True


def construire(
    note: Note,
    constat: ConstatType,
    prefixe_systeme: str,
    taille_max_note: int,
    *,
    langue: Langue = "fr",
) -> list[Message]:
    """Messages `[system, user]` ; `constat_attendu` et les références n'y figurent jamais.

    [v2] CAP-8 : consigne et textes du constat dans `langue` (contrats §8, §23).
    """
    consigne = CONSIGNES[langue]
    systeme = f"{prefixe_systeme}\n{consigne}" if prefixe_systeme else consigne
    textes = constat.textes(langue)
    champs_constat = {"id": constat.id, **textes.model_dump(), "cvss_vecteur": constat.cvss_vecteur}
    donnees_constat = json.dumps(champs_constat, ensure_ascii=False)
    corps, _ = tronquer(echapper(note.corps), taille_max_note)
    actif = f"{_LIBELLE_ACTIF[langue]}{echapper(note.actif)}\n" if note.actif else ""
    utilisateur = f"<constat>{donnees_constat}</constat>\n<note>{actif}{corps}</note>"
    return [
        {"role": "system", "content": systeme},
        {"role": "user", "content": utilisateur},
    ]
