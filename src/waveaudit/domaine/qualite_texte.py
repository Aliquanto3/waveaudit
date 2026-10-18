"""Qualité du texte généré par le moteur : répétition et langue (contrats §6 v2, §21 v2).

Module stdlib seule, partagé par `domaine/garde_fous.py` (fiches) et
`domaine/garde_fous_incident.py` (incident). `source` est le texte où une citation littérale
(payload, fragment de note ou de preuve) ne doit pas déclencher un faux positif : une
sous-chaîne de `texte` qui figure aussi, telle quelle, dans `source` est ignorée.
"""

import re
import unicodedata

from waveaudit.domaine.modeles import Langue

# --- Répétition (étape 5) ------------------------------------------------------------------

_TRIGRAMMES_MIN = 10
_RATIO_MIN = 0.30
_BOUCLE = re.compile(r"(.{3,50}?)\1{4,}", re.DOTALL)
_LONGUEUR_BOUCLE_MIN = 40
_UNE_LETTRE = re.compile(r"[^\W\d_]", re.UNICODE)


def _mots(texte: str) -> list[str]:
    return re.findall(r"\w+", texte.lower(), re.UNICODE)


def _trigrammes_peu_varies(texte: str) -> bool:
    mots = _mots(texte)
    trigrammes = [tuple(mots[i : i + 3]) for i in range(len(mots) - 2)]
    if len(trigrammes) < _TRIGRAMMES_MIN:
        return False
    ratio = 1 - len(set(trigrammes)) / len(trigrammes)
    return ratio >= _RATIO_MIN


def _boucle_sans_espace(texte: str, source: str) -> bool:
    source_cf = source.casefold()
    for correspondance in _BOUCLE.finditer(texte):
        motif_repete = correspondance.group(0)
        if len(motif_repete) < _LONGUEUR_BOUCLE_MIN:
            continue
        if _UNE_LETTRE.search(motif_repete) is None:
            continue
        if source and motif_repete.casefold() in source_cf:
            continue  # charge ou valeur citée (note, actif, preuves…) : pas une boucle
        return True
    return False


def est_repetitif(texte: str, source: str = "") -> bool:
    """Contrats §6 étape 5 / §21 : trigrammes peu variés, ou boucle sans espace non citée."""
    return _trigrammes_peu_varies(texte) or _boucle_sans_espace(texte, source)


# --- Langue (étape 6) ----------------------------------------------------------------------

_LETTRES_TOLEREES = frozenset("µªº")


def _lettre_non_latine(caractere: str) -> bool:
    if caractere in _LETTRES_TOLEREES:
        return False
    if unicodedata.category(caractere) not in ("Lu", "Ll", "Lt", "Lo"):
        return False  # catégorie Lm (ʼ, ˆ) et autres : tolérées
    return not unicodedata.name(caractere, "").startswith("LATIN")


def _ecriture_non_latine(texte: str, source: str) -> bool:
    """Contrats §6 étape 6 (revue E35/E36) : la comparaison à la source se fait par lettre.

    Une lettre non latine présente dans la source (note ou preuves) est une citation ; la
    comparer par jeton séparé par des espaces ferait d'une ponctuation collée (« Жертва, »)
    un faux positif.
    """
    lettres_source = set(source) | set(source.casefold())
    return any(
        _lettre_non_latine(c) and c not in lettres_source and c.casefold() not in lettres_source
        for c in texte
    )


_CITATIONS = re.compile(r'"[^"]*"|“[^”]*”|«[^»]*»|`[^`]*`')
_MOT_LANGUE = re.compile(r"(?<!\w)[^\W\d_]+(?!\w)", re.UNICODE)

#: Listes figées (contrats §6 étape 6), sans mot ambigu entre les deux langues.
MOTS_OUTILS: dict[Langue, frozenset[str]] = {
    "fr": frozenset(
        "le la les un une des du de et est sont dans pour par sur avec qui que ne pas au aux "
        "ce cette ces leur leurs il elle ils peut permet afin être son sa ses d l qu".split()
    ),
    "en": frozenset(
        "the of and is are to in for with that this which by be can could should may from it "
        "its not allows into their has have will".split()
    ),
}


def _autre_langue(langue: Langue) -> Langue:
    return "en" if langue == "fr" else "fr"


def _mots_comptes(texte: str) -> list[str]:
    """Mots hors segments cités, hors sigles tout capitales, en minuscules."""
    sans_citations = _CITATIONS.sub(" ", texte)
    mots: list[str] = []
    for mot in _MOT_LANGUE.findall(sans_citations):
        if mot.isupper() and len(mot) >= 2:
            continue  # sigle : IT, IS, TO, DES…
        mots.append(mot.lower())
    return mots


def _mots_outils_etrangers(texte: str, langue: Langue) -> Langue | None:
    mots = _mots_comptes(texte)
    autre = _autre_langue(langue)
    n_cible = sum(1 for mot in mots if mot in MOTS_OUTILS[langue])
    n_autre = sum(1 for mot in mots if mot in MOTS_OUTILS[autre])
    if n_autre >= 2 and n_autre > n_cible:
        return autre
    return None


def motif_langue(
    texte: str,
    langue: Langue,
    source: str = "",
    *,
    verifier_mots_outils: bool = True,
) -> str | None:
    """Contrats §6 étape 6 / §21. Renvoie le suffixe du détail (sans le nom de rubrique) :

    `"écriture non latine"` ou `"mots-outils <autre langue>"`, ou `None` si rien à signaler.
    `verifier_mots_outils=False` pour le titre (jamais soumis aux mots-outils, contrats §6).
    """
    if _ecriture_non_latine(texte, source):
        return "écriture non latine"
    if verifier_mots_outils:
        autre = _mots_outils_etrangers(texte, langue)
        if autre is not None:
            return f"mots-outils {autre}"
    return None
