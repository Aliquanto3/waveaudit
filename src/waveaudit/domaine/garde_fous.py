"""Garde-fous appliqués à la sortie du moteur avant publication (contrats §6, AD-5)."""

import re
from collections.abc import Sequence

from pydantic import ValidationError

from waveaudit.domaine import cvss31
from waveaudit.domaine.modeles import (
    RUBRIQUES,
    Candidat,
    CodeMotif,
    ConstatType,
    Cvss,
    Fiche,
    Langue,
    MetriquesCvss,
    Motif,
    Note,
    Statut,
    Tracabilite,
)
from waveaudit.domaine.qualite_texte import est_repetitif, motif_langue

LONGUEUR_MIN_TITRE = 5
LONGUEUR_MIN_RUBRIQUE = 20

_URL = re.compile(r"https?://\S+")

_MOTIFS_REFERENCES: tuple[str, ...] = (
    r"CWE-\d+",
    r"CVE-\d{4}-\d+",
    r"CAPEC-\d+",
    r"WSTG-[A-Z]+-\d+",
    r"A\d{2}:20\d{2}",
    r"ANSSI-[A-Z0-9-]+",
    r"CERTFR-\d{4}-[A-Z]{3}-\d{3}",
    r"https?://\S+",
)
_REGEX_REFERENCES = re.compile(
    "|".join(f"(?:{motif})" for motif in _MOTIFS_REFERENCES), re.IGNORECASE
)
_PONCTUATION_FINALE = ".,;:)]}>\"'"


def _nettoyer_url(jeton: str) -> str:
    return jeton.rstrip(_PONCTUATION_FINALE)


def _urls_de_la_note(note: Note) -> set[str]:
    """Jetons URL entiers de `note.corps` et `note.actif` (note entière, pas tronquée)."""
    texte = note.corps + ("\n" + note.actif if note.actif else "")
    return {_nettoyer_url(m.group(0)) for m in _URL.finditer(texte)}


def _texte_source(note: Note) -> str:
    """Texte source d'une citation (étapes 5 et 6) : note entière, corps et actif."""
    return note.corps + ("\n" + note.actif if note.actif else "")


def _retirer_references_inventees(
    texte: str, ids_valides: set[str], urls_valides: set[str]
) -> tuple[str, list[str]]:
    """Retire les identifiants et URL de la rubrique qui ne sont pas ceux du constat type

    ni, pour une URL, un jeton entier présent dans `note.corps` ou `note.actif` (contrats §6
    v2, revue A20/E39) : `urls_valides` porte déjà cette union.
    """
    jetons_retires: list[str] = []

    def _remplacer(correspondance: re.Match[str]) -> str:
        jeton = correspondance.group(0)
        if jeton.lower().startswith(("http://", "https://")):
            if _nettoyer_url(jeton) in urls_valides:
                return jeton
        elif jeton.upper() in ids_valides:
            return jeton
        jetons_retires.append(jeton)
        return ""

    nettoye = _REGEX_REFERENCES.sub(_remplacer, texte)
    nettoye = re.sub(r"\(\s*\)", "", nettoye)
    nettoye = re.sub(r"\[\s*\]", "", nettoye)
    # Espaces horizontaux normalisés ; les sauts de ligne (listes, paragraphes) sont conservés.
    nettoye = re.sub(r"[^\S\n]+", " ", nettoye)
    nettoye = re.sub(r" *\n *", "\n", nettoye).strip()
    return nettoye, jetons_retires


def _evaluer_metriques(sortie_brute: dict, constat: ConstatType) -> tuple[Cvss, Motif | None]:
    brut = sortie_brute.get("cvss")
    if isinstance(brut, dict):
        try:
            metriques = MetriquesCvss(**brut)
        except (ValidationError, TypeError):
            metriques = None
    else:
        metriques = None
    if metriques is not None:
        return cvss31.evaluer(cvss31.vecteur(metriques)), None
    return (
        cvss31.evaluer(constat.cvss_vecteur),
        Motif(code=CodeMotif.VECTEUR_INVALIDE, detail=constat.cvss_vecteur),
    )


def appliquer(
    sortie_brute: dict,
    constat: ConstatType,
    note: Note,
    candidats: list[Candidat],
    longueur_max: int,
    *,
    motifs_initiaux: Sequence[Motif] = (),
    langue: Langue = "fr",
) -> Fiche:
    """Applique les garde-fous (contrats §6 v2, ordre révisé CAP-3/CAP-4) à la sortie brute."""
    motifs: list[Motif] = list(motifs_initiaux)
    references = list(constat.references)
    ids_valides = {reference.id.upper() for reference in references}
    urls_valides = {reference.url for reference in references} | _urls_de_la_note(note)

    textes_constat = constat.textes(langue)
    textes_constat_dict = {
        "titre": textes_constat.titre,
        "description": textes_constat.description,
        "impact": textes_constat.impact,
        "recommandation": textes_constat.recommandation,
    }

    rubriques: dict[str, str] = {}
    for nom in RUBRIQUES:
        brut = sortie_brute.get(nom, "")
        texte = brut if isinstance(brut, str) else ""
        texte, jetons_retires = _retirer_references_inventees(texte, ids_valides, urls_valides)
        for jeton in jetons_retires:
            motifs.append(Motif(code=CodeMotif.REFERENCE_RETIREE, detail=jeton))
        rubriques[nom] = texte

    cvss, motif_vecteur = _evaluer_metriques(sortie_brute, constat)
    if motif_vecteur is not None:
        motifs.append(motif_vecteur)

    completees: set[str] = set()
    for nom in RUBRIQUES:
        texte = rubriques[nom]
        minimum = LONGUEUR_MIN_TITRE if nom == "titre" else LONGUEUR_MIN_RUBRIQUE
        if len(texte) < minimum:
            texte = textes_constat_dict[nom]
            motifs.append(Motif(code=CodeMotif.RUBRIQUE_COMPLETEE, detail=nom))
            completees.add(nom)
        rubriques[nom] = texte[:longueur_max]

    # [v2] Étapes 5 (répétition) et 6 (langue), sur les rubriques non complétées à l'étape 4.
    source = _texte_source(note)
    for nom in RUBRIQUES:
        if nom in completees:
            continue
        if est_repetitif(rubriques[nom], source):
            motifs.append(Motif(code=CodeMotif.REPETITION, detail=nom))

    for nom in RUBRIQUES:
        if nom in completees:
            continue
        detail = motif_langue(rubriques[nom], langue, source, verifier_mots_outils=(nom != "titre"))
        if detail is not None:
            motifs.append(Motif(code=CodeMotif.LANGUE, detail=f"{nom} : {detail}"))

    statut = Statut.A_REVOIR if motifs else Statut.OK

    return Fiche(
        titre=rubriques["titre"],
        description=rubriques["description"],
        impact=rubriques["impact"],
        recommandation=rubriques["recommandation"],
        cvss=cvss,
        references=references,
        statut=statut,
        motifs=motifs,
        tracabilite=Tracabilite(
            note=note.fichier,
            constat_id=constat.id,
            candidats=candidats,
            constat_attendu=note.constat_attendu,
        ),
    )
