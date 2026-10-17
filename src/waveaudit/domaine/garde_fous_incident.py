"""Garde-fous du récit généré par le workflow incident (contrats §21, CAP-5).

Décision d'orchestration (consignée dans les reports de C1) : les motifs normatifs de
`domaine.incident` (`MOTIF_TECHNIQUE`, `MOTIF_IPV4`, `MOTIF_IPV6`, `MOTIF_HACHAGE`) ratent un
jeton suivi d'un point final de phrase (leur lookahead `(?![\\d.])` ou la gloutonnerie de
`MOTIF_IPV6` sont figés par `test_motifs_point_final_comportement_fige` et ne sont pas
modifiés). Ce module les applique sur une **copie** du texte, de même longueur, où chaque
suite de « . » suivie d'un blanc, de la fin du texte ou d'une ponctuation fermante ou
séparatrice (`) ] } > » " ' ” ’ , ; : ! ?`) est remplacée par autant d'espaces ; les
positions des jetons trouvés restent valables pour retirer le jeton du texte d'origine. Un
« . » suivi d'un chiffre (`T1110.001`, `10.0.19045`, `::ffff:192.0.2.10`) n'est jamais touché.
"""

import ipaddress
import re
from collections.abc import Sequence

from waveaudit.domaine.incident import (
    MOTIF_HACHAGE,
    MOTIF_IPV4,
    MOTIF_IPV6,
    MOTIF_TECHNIQUE,
    RUBRIQUES_RECIT,
    Detection,
    Recit,
    Regle,
)
from waveaudit.domaine.modeles import CodeMotif, Motif, Statut

_LONGUEUR_MIN_RUBRIQUE = 20
_POINT_FINAL = re.compile(r"\.+(?=[\s)\]}>»\"'”’,;:!?]|\Z)")


def _copie_sans_point_final(texte: str) -> str:
    """Même longueur que `texte` : chaque « . » de fin de phrase devient une espace."""
    return _POINT_FINAL.sub(lambda m: " " * len(m.group(0)), texte)


def _normaliser_ip(candidat: str) -> str | None:
    try:
        ip = ipaddress.ip_address(candidat)
    except ValueError:
        return None
    if isinstance(ip, ipaddress.IPv6Address):
        mappee = ip.ipv4_mapped
        if mappee is not None:
            ip = mappee
    return str(ip)


def _retirer(
    texte: str, decisions: list[tuple[int, int, str]], code: CodeMotif
) -> tuple[str, list[Motif]]:
    """Retire du texte d'origine les jetons dont les positions ont été repérées sur la copie."""
    if not decisions:
        return texte, []
    decisions = sorted(decisions)
    morceaux: list[str] = []
    motifs: list[Motif] = []
    position = 0
    for debut, fin, jeton in decisions:
        if debut < position:
            continue  # chevauchement : déjà traité
        morceaux.append(texte[position:debut])
        position = fin
        motifs.append(Motif(code=code, detail=jeton))
    morceaux.append(texte[position:])
    return "".join(morceaux), motifs


def _traiter_techniques(texte: str, ids_valides: set[str]) -> tuple[str, list[Motif]]:
    """Étape 2 de §21 : jeton `MOTIF_TECHNIQUE` gardé ssi `upper()` est une référence exacte."""
    copie = _copie_sans_point_final(texte)
    decisions: list[tuple[int, int, str]] = []
    for correspondance in MOTIF_TECHNIQUE.finditer(copie):
        debut, fin = correspondance.span()
        jeton = texte[debut:fin]
        if jeton.upper() not in ids_valides:
            decisions.append((debut, fin, jeton))
    return _retirer(texte, decisions, CodeMotif.REFERENCE_RETIREE)


def _traiter_indicateurs(
    texte: str, ips_valides: set[str], hachages_valides: set[str]
) -> tuple[str, list[Motif]]:
    """Étape 3 de §21 : IPv6 traités d'abord, IPv4 inclus dans une IPv6 non retraités."""
    copie = _copie_sans_point_final(texte)
    decisions: list[tuple[int, int, str]] = []
    spans_ipv6: list[tuple[int, int]] = []

    for correspondance in MOTIF_IPV6.finditer(copie):
        debut, fin = correspondance.span()
        jeton = texte[debut:fin]
        normalisee = _normaliser_ip(jeton)
        if normalisee is None:
            continue  # candidat invalide : laissé tel quel
        spans_ipv6.append((debut, fin))
        if normalisee not in ips_valides:
            decisions.append((debut, fin, jeton))

    for correspondance in MOTIF_IPV4.finditer(copie):
        debut, fin = correspondance.span()
        if any(a <= debut and fin <= b for a, b in spans_ipv6):
            continue  # déjà traité comme partie d'une IPv6 valide
        jeton = texte[debut:fin]
        normalisee = _normaliser_ip(jeton)
        if normalisee is None:
            continue
        if normalisee not in ips_valides:
            decisions.append((debut, fin, jeton))

    for correspondance in MOTIF_HACHAGE.finditer(copie):
        debut, fin = correspondance.span()
        jeton = texte[debut:fin]
        if jeton.lower() not in hachages_valides:
            decisions.append((debut, fin, jeton))

    return _retirer(texte, decisions, CodeMotif.INDICATEUR_RETIRE)


def _nettoyer_espaces(texte: str) -> str:
    texte = re.sub(r"\(\s*\)", "", texte)
    texte = re.sub(r"\[\s*\]", "", texte)
    texte = re.sub(r"[^\S\n]+", " ", texte)
    texte = re.sub(r" *\n *", "\n", texte).strip()
    return texte


def appliquer_recit(
    sortie_brute: dict,
    regle: Regle,
    detection: Detection,
    longueur_max: int,
    motifs_initiaux: Sequence[Motif] = (),
) -> Recit:
    """Garde-fous du récit (contrats §21). `detection.indicateurs` doit être déjà rempli."""
    motifs: list[Motif] = list(motifs_initiaux)
    references = list(regle.references)
    ids_valides = {reference.id.upper() for reference in references}
    ips_valides = {i.valeur for i in detection.indicateurs if i.type == "ip"}
    hachages_valides = {i.valeur for i in detection.indicateurs if i.type == "hachage"}

    textes_regle = {
        "titre": regle.titre,
        "recit": regle.description,
        "impact": regle.impact,
        "recommandation": regle.recommandation,
    }

    rubriques: dict[str, str] = {}
    for nom in RUBRIQUES_RECIT:
        brut = sortie_brute.get(nom, "")
        texte = brut if isinstance(brut, str) else ""
        texte, motifs_techniques = _traiter_techniques(texte, ids_valides)
        motifs.extend(motifs_techniques)
        texte, motifs_indicateurs = _traiter_indicateurs(texte, ips_valides, hachages_valides)
        motifs.extend(motifs_indicateurs)
        rubriques[nom] = _nettoyer_espaces(texte)

    for nom in RUBRIQUES_RECIT:
        texte = rubriques[nom]
        if nom == "titre":
            if not texte:
                texte = regle.titre
                motifs.append(Motif(code=CodeMotif.RUBRIQUE_COMPLETEE, detail=nom))
        elif len(texte) < _LONGUEUR_MIN_RUBRIQUE:
            texte = textes_regle[nom]
            motifs.append(Motif(code=CodeMotif.RUBRIQUE_COMPLETEE, detail=nom))
        rubriques[nom] = texte[:longueur_max]

    statut = Statut.A_REVOIR if motifs else Statut.OK

    return Recit(
        detection=detection,
        regle_titre=regle.titre,
        titre=rubriques["titre"],
        recit=rubriques["recit"],
        impact=rubriques["impact"],
        recommandation=rubriques["recommandation"],
        severite=regle.severite,
        references=references,
        statut=statut,
        motifs=motifs,
    )
