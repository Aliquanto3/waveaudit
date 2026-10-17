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
    MetriquesCvss,
    Motif,
    Note,
    Statut,
    Tracabilite,
)

_LONGUEUR_MIN_RUBRIQUE = 20

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


def _retirer_references_inventees(
    texte: str, ids_valides: set[str], urls_valides: set[str]
) -> tuple[str, list[str]]:
    """Retire les identifiants et URL de la rubrique qui ne sont pas ceux du constat type."""
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
    nettoye = re.sub(r"\s+", " ", nettoye).strip()
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
) -> Fiche:
    """Applique les garde-fous (contrats §6) à la sortie brute du moteur et produit une Fiche."""
    motifs: list[Motif] = list(motifs_initiaux)
    references = list(constat.references)
    ids_valides = {reference.id.upper() for reference in references}
    urls_valides = {reference.url for reference in references}

    textes_constat = {
        "titre": constat.titre,
        "description": constat.description,
        "impact": constat.impact,
        "recommandation": constat.recommandation,
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

    for nom in RUBRIQUES:
        texte = rubriques[nom]
        if len(texte) < _LONGUEUR_MIN_RUBRIQUE:
            rubriques[nom] = textes_constat[nom]
            motifs.append(Motif(code=CodeMotif.RUBRIQUE_COMPLETEE, detail=nom))
        elif len(texte) > longueur_max:
            rubriques[nom] = texte[:longueur_max]

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
