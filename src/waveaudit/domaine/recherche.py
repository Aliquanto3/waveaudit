"""Recherche BM25 des constats types pour une note (contrats §7, CAP-3)."""

import re
import unicodedata
from collections import Counter
from math import log

from waveaudit.domaine.modeles import Candidat, ConstatType, Note

_MOTS_VIDES: frozenset[str] = frozenset(
    {
        # français
        "le",
        "la",
        "les",
        "un",
        "une",
        "des",
        "de",
        "du",
        "et",
        "ou",
        "est",
        "en",
        "dans",
        "sur",
        "pour",
        "par",
        "au",
        "aux",
        "ce",
        "ces",
        "cet",
        "cette",
        "son",
        "sa",
        "ses",
        "qui",
        "que",
        "quoi",
        "dont",
        "ne",
        "pas",
        "plus",
        "avec",
        "sans",
        "se",
        "leur",
        "leurs",
        "il",
        "elle",
        "ils",
        "elles",
        "nous",
        "vous",
        "je",
        "tu",
        "on",
        "d",
        "l",
        "n",
        "s",
        "c",
        "qu",
        "y",
        "mais",
        "si",
        "ete",
        "etre",
        "avoir",
        "fait",
        "faire",
        "tout",
        "tous",
        "toute",
        "toutes",
        "comme",
        "aussi",
        "alors",
        # anglais
        "the",
        "a",
        "an",
        "and",
        "or",
        "is",
        "in",
        "for",
        "by",
        "at",
        "to",
        "of",
        "with",
        "without",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
        "be",
        "are",
        "was",
        "were",
        "as",
        "from",
        "not",
        "but",
        "if",
        "then",
        "so",
        "all",
        "any",
        "has",
        "have",
        "had",
    }
)

_SEPARATEURS = re.compile(r"[^a-z0-9]+")
# NFKD ne décompose pas ces ligatures : sans cela « œuvre » donnerait « uvre ».
_LIGATURES = str.maketrans({"œ": "oe", "æ": "ae", "ß": "ss"})


def _tokeniser(texte: str) -> list[str]:
    """Minuscules, NFKD sans diacritique, découpage non-alphanumérique, jetons >=2 sans mot vide."""
    normalise = unicodedata.normalize("NFKD", texte.lower().translate(_LIGATURES))
    sans_diacritiques = "".join(c for c in normalise if not unicodedata.combining(c))
    jetons = _SEPARATEURS.split(sans_diacritiques)
    return [j for j in jetons if len(j) >= 2 and j not in _MOTS_VIDES]


def _document(constat: ConstatType) -> list[str]:
    """Index bilingue (contrats §7 v2) : titre fr ×3, en.titre ×3 (si présent), mots-clés
    joints ×3, description fr ×1, en.description ×1 (si présent), concaténés."""
    morceaux = [constat.titre] * 3
    if constat.en is not None:
        morceaux += [constat.en.titre] * 3
    morceaux += [" ".join(constat.mots_cles)] * 3
    morceaux.append(constat.description)
    if constat.en is not None:
        morceaux.append(constat.en.description)
    jetons: list[str] = []
    for morceau in morceaux:
        jetons.extend(_tokeniser(morceau))
    return jetons


def classer(constats: list[ConstatType], requete: str, *, k1: float, b: float) -> list[Candidat]:
    """BM25 classique ; renvoie tous les constats triés score décroissant puis id croissant."""
    jetons_requete = _tokeniser(requete)
    if not constats:
        return []

    documents: dict[str, list[str]] = {c.id: _document(c) for c in constats}
    longueurs: dict[str, int] = {cid: len(jetons) for cid, jetons in documents.items()}
    n_docs = len(constats)
    avgdl = sum(longueurs.values()) / n_docs if n_docs else 0.0

    frequences: dict[str, Counter[str]] = {
        cid: Counter(jetons) for cid, jetons in documents.items()
    }

    idf: dict[str, float] = {}
    for jeton in set(jetons_requete):
        n_contenant = sum(1 for freq in frequences.values() if freq[jeton] > 0)
        idf[jeton] = log(1 + (n_docs - n_contenant + 0.5) / (n_contenant + 0.5))

    candidats: list[Candidat] = []
    for constat in constats:
        freq = frequences[constat.id]
        dl = longueurs[constat.id]
        score = 0.0
        for jeton in jetons_requete:
            tf = freq[jeton]
            if tf == 0:
                continue
            denominateur = tf + k1 * (1 - b + b * (dl / avgdl if avgdl else 0.0))
            score += idf[jeton] * (tf * (k1 + 1)) / denominateur
        candidats.append(Candidat(id=constat.id, score=score))

    candidats.sort(key=lambda c: (-c.score, c.id))
    return candidats


def requete_depuis_note(note: Note) -> str:
    """Texte de requête (contrats §7) : titre puis corps, jamais `constat_attendu` ni `actif`."""
    return (note.titre or "") + "\n" + note.corps
