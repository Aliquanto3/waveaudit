"""Moteur de détection déterministe (CAP-2, CAP-3, contrats §21 « Détection »).

`detecter` laisse `Detection.indicateurs` vide : les indicateurs sont extraits par le
pipeline (C4, C5), jamais ici. Ce module n'importe pas `domaine.indicateurs`.
"""

import re

from waveaudit.domaine.incident import Detection, Evenement, Regle


def correspond(regle: Regle, evenement: Evenement) -> bool:
    """Applicabilité seule (source et critères de `Regle.condition`), sans agrégation."""
    if regle.source != evenement.source:
        return False
    condition = regle.condition

    if condition.event_id is not None and evenement.event_id not in condition.event_id:
        return False

    if condition.log_name is not None:
        if evenement.log_name is None:
            return False
        if evenement.log_name.casefold() != condition.log_name.casefold():
            return False

    if condition.programme is not None:
        if evenement.programme is None:
            return False
        if evenement.programme.casefold() != condition.programme.casefold():
            return False

    for cle, valeur in condition.champs.items():
        courante = evenement.champs.get(cle)
        if courante is None or courante.casefold() != valeur.casefold():
            return False

    for cle, motif in condition.champs_regex.items():
        courante = evenement.champs.get(cle)
        if courante is None or not re.search(motif, courante, re.IGNORECASE):
            return False

    if condition.au_moins_un:
        if not any(
            (courante := evenement.champs.get(cle)) is not None
            and re.search(motif, courante, re.IGNORECASE)
            for cle, motif in condition.au_moins_un.items()
        ):
            return False

    if condition.message_regex is not None and not re.search(
        condition.message_regex, evenement.message, re.IGNORECASE
    ):
        return False

    return True


def detecter(regles: list[Regle], evenements: list[Evenement]) -> list[Detection]:
    """Applique chaque règle aux événements et renvoie les détections (contrats §21).

    Sans agrégation : une détection par événement correspondant. Avec agrégation : les
    événements correspondants et porteurs de tous les champs `par` sont groupés par les
    valeurs (`casefold`) de ces champs, triés, puis regroupés en fenêtres glissantes
    (algorithme normatif de contrats §21).
    """
    resultats: list[Detection] = []
    for regle in regles:
        correspondants = [e for e in evenements if correspond(regle, e)]
        if regle.agregation is None:
            for e in correspondants:
                resultats.append(
                    Detection(
                        regle_id=regle.id,
                        debut=e.horodatage,
                        fin=e.horodatage,
                        hotes=[e.hote],
                        evenements=[e],
                    )
                )
        else:
            resultats.extend(_detecter_agrege(regle, correspondants))

    def _cle_tri(d: Detection) -> tuple:
        premier = d.evenements[0]
        return (d.debut, d.regle_id, premier.fichier.casefold(), premier.ligne)

    resultats.sort(key=_cle_tri)
    return resultats


def _detecter_agrege(regle: Regle, correspondants: list[Evenement]) -> list[Detection]:
    agregation = regle.agregation
    assert agregation is not None

    groupes: dict[tuple[str, ...], list[Evenement]] = {}
    for e in correspondants:
        valeurs: list[str] = []
        complet = True
        for cle in agregation.par:
            valeur = e.champs.get(cle)
            if valeur is None:
                complet = False
                break
            valeurs.append(valeur.casefold())
        if not complet:
            continue
        groupes.setdefault(tuple(valeurs), []).append(e)

    resultats: list[Detection] = []
    for groupe in groupes.values():
        groupe = sorted(groupe, key=lambda e: (e.horodatage, e.fichier.casefold(), e.ligne))
        t = [e.horodatage.timestamp() for e in groupe]
        for d, f in _fenetres(t, agregation.seuil, agregation.fenetre_s):
            sous_groupe = groupe[d : f + 1]
            resultats.append(
                Detection(
                    regle_id=regle.id,
                    debut=sous_groupe[0].horodatage,
                    fin=sous_groupe[-1].horodatage,
                    hotes=sorted({e.hote for e in sous_groupe}, key=str.casefold),
                    evenements=sous_groupe,
                )
            )

    return resultats


def _fenetres(t: list[float], seuil: int, fenetre: float) -> list[tuple[int, int]]:
    """Bornes `(d, f)` incluses des fenêtres du pseudo-code de contrats §21, en O(n).

    `t` est trié. Pour un indice `k`, les `j <= k` tels que `t[k] - t[j] <= fenetre`
    forment un suffixe `[lo(k), k]`, avec `lo` croissant en `k` ; et `k`, `f` ne font
    qu'avancer d'une itération à l'autre (`i = f + 1`). Un seul pointeur `lo` suffit
    donc : `#{j : a <= j <= k et t[k] - t[j] <= fenetre} = k - max(a, lo(k)) + 1`.
    Mêmes comparaisons que le pseudo-code, donc mêmes résultats.
    """
    n = len(t)
    lo = 0

    def avancer(k: int) -> None:
        nonlocal lo
        while t[k] - t[lo] > fenetre:
            lo += 1

    fenetres: list[tuple[int, int]] = []
    i = 0
    while i < n:
        k = i
        while k < n:
            avancer(k)
            if k - max(i, lo) + 1 >= seuil:
                break
            k += 1
        if k >= n:
            break
        d = max(i, lo)
        f = k
        while f + 1 < n:
            avancer(f + 1)
            if (f + 1) - max(d, lo) + 1 >= seuil:
                f += 1
            else:
                break
        fenetres.append((d, f))
        i = f + 1
    return fenetres
