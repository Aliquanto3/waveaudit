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
        "Tu es un assistant de rédaction d'audit de sécurité. Le constat type fourni entre les "
        "balises <constat> est un modèle générique. Adapte-le aux observations de la note "
        "d'audit fournie entre les balises <note> : rédige en français professionnel la fiche "
        "de ce cas précis, avec les rubriques titre, description, impact et recommandation.\n"
        "- titre : un nouveau titre pour ce cas, qui nomme la vulnérabilité et l'actif touché "
        "tel que la note le désigne ; ne reprends pas le titre du constat type.\n"
        "- description : ce que l'auditeur a constaté (actif, test mené, résultat obtenu), avec "
        "les faits précis de la note ; ne recopie pas la description générique.\n"
        "- impact : en une ou deux phrases, ce que la faille permet ici, avec l'actif et les "
        "données de la note ; ne recopie pas l'impact générique.\n"
        "- recommandation : en deux ou trois phrases, les actions qui corrigent ce cas, en "
        "t'appuyant sur le constat type.\n"
        "- N'invente aucun identifiant, aucune référence, aucune URL ni aucun fait absent de la "
        "note ; ne présente pas comme constaté ce que la note n'a pas vérifié.\n"
        "- Garde le vecteur CVSS par défaut du constat type, sauf si la note le contredit.\n"
        "- Réponds uniquement par un objet JSON conforme au schéma demandé."
    ),
    "en": (
        "You are a security audit writing assistant. The constat type given between the "
        "<constat> tags is a generic template. Adapt it to the observations of the audit note "
        "given between the <note> tags: write in professional English the finding for this "
        "specific case, with the titre, description, impact and recommandation sections.\n"
        "- titre: a new title for this case, naming the vulnerability and the affected asset "
        "as the note designates it; do not reuse the constat type's title.\n"
        "- description: what the auditor observed (asset, test performed, result obtained), "
        "with the precise facts of the note; do not copy the generic description.\n"
        "- impact: in one or two sentences, what the flaw allows here, with the asset and the "
        "data of the note; do not copy the generic impact.\n"
        "- recommandation: in two or three sentences, the actions that fix this case, based on "
        "the constat type.\n"
        "- Do not invent any identifier, reference, URL or fact absent from the note; do not "
        "present as observed what the note did not verify.\n"
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
