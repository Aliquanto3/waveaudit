"""Vecteurs CVSS 3.1 (contrats §6). Seul module autorisé à importer `cvss` (story 3 : `evaluer`)."""

from cvss import CVSS3
from cvss.exceptions import CVSS3MalformedError, CVSS3MandatoryError
from pydantic import ValidationError

from waveaudit.domaine.erreurs import EntreeInvalide
from waveaudit.domaine.modeles import Cvss, MetriquesCvss

PREFIXE = "CVSS:3.1/"
ORDRE: tuple[str, ...] = tuple(MetriquesCvss.model_fields)  # AV/AC/PR/UI/S/C/I/A

_SEVERITES: dict[str, str] = {
    "None": "aucune",
    "Low": "faible",
    "Medium": "moyenne",
    "High": "elevee",
    "Critical": "critique",
}


def vecteur(m: MetriquesCvss) -> str:
    """Vecteur canonique : préfixe puis les 8 métriques de base dans l'ordre AV/AC/PR/UI/S/C/I/A."""
    return PREFIXE + "/".join(f"{nom}:{getattr(m, nom)}" for nom in ORDRE)


def metriques_depuis_vecteur(v: str) -> MetriquesCvss:
    """Lit exactement les 8 métriques de base ; lève EntreeInvalide sinon.

    L'ordre des métriques n'est pas imposé ici : `vecteur(...)` le recanonise toujours en
    AV/AC/PR/UI/S/C/I/A. Pour exiger la forme canonique (catalogue, `verifier`), comparer
    `vecteur(metriques_depuis_vecteur(v)) == v`.
    """
    if not isinstance(v, str) or not v.startswith(PREFIXE):
        raise EntreeInvalide(f"vecteur CVSS 3.1 invalide (préfixe {PREFIXE} attendu) : {v!r}")
    valeurs: dict[str, str] = {}
    for morceau in v[len(PREFIXE) :].split("/"):
        nom, separateur, valeur = morceau.partition(":")
        if not separateur or nom not in ORDRE or nom in valeurs:
            raise EntreeInvalide(f"vecteur CVSS 3.1 invalide (métrique {morceau!r}) : {v!r}")
        valeurs[nom] = valeur
    if len(valeurs) != len(ORDRE):
        manquantes = ", ".join(nom for nom in ORDRE if nom not in valeurs)
        raise EntreeInvalide(f"vecteur CVSS 3.1 invalide (manque {manquantes}) : {v!r}")
    try:
        return MetriquesCvss(**valeurs)
    except ValidationError as erreur:
        raise EntreeInvalide(f"vecteur CVSS 3.1 invalide (valeur hors enum) : {v!r}") from erreur


def evaluer(v: str) -> Cvss:
    """Score et sévérité de base pour un vecteur CVSS 3.1 (contrats §6)."""
    try:
        base = CVSS3(v)
    except (CVSS3MalformedError, CVSS3MandatoryError) as erreur:
        raise EntreeInvalide(f"vecteur CVSS 3.1 invalide : {v!r}") from erreur
    score = base.scores()[0]
    severite = _SEVERITES[base.severities()[0]]
    return Cvss(vecteur=v, score=score, severite=severite)
