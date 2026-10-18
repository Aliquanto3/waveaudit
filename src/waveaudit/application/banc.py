"""Banc de mesure : lot instrumenté en mémoire et en durées (contrats §20, CAP-12).

Le banc s'abonne au lot (AD-2) : il démarre un échantillonnage de `MesureMemoire.rss_octets`
(contrats §9, `composition.creer_mesure_memoire`) à `lot_demarre` — qui porte `pid_moteur` — et
l'arrête à `lot_termine` ou `lot_echoue`. `top1`/`top3`/`etiquetees` sont recalculés depuis la
traçabilité des fiches et des entrées écartées (contrats §20).
"""

import difflib
import json
import logging
import os
import statistics
import threading
from collections import Counter
from pathlib import Path

from waveaudit.application import composition
from waveaudit.application.lot import executer_lot
from waveaudit.domaine.configuration import Configuration
from waveaudit.domaine.modeles import (
    RUBRIQUES,
    Candidat,
    CodeMotif,
    EvenementLot,
    Fiche,
    Langue,
    Rapport,
    RequeteLot,
    Statut,
    TypeEvenement,
)
from waveaudit.domaine.ports import Catalogue, MesureMemoire

_log = logging.getLogger(__name__)
INTERVALLE_S = 0.5
FICHIER = "banc.json"
# [v2] Fiches de repli (texte du catalogue par construction) : exclues de la recopie (§29).
_MOTIFS_REPLI = frozenset({CodeMotif.REPLI_SORTIE_INVALIDE, CodeMotif.REPLI_MOTEUR})


class _Echantillonneur:
    """Échantillonne la RSS de l'application et, si connue, du moteur, dans un fil dédié."""

    def __init__(self, mesure: MesureMemoire, pid_app: int) -> None:
        self._mesure = mesure
        self._pid_app = pid_app
        self._pid_moteur: int | None = None
        self._arret = threading.Event()
        self._fil: threading.Thread | None = None
        self.app: list[int] = []
        self.moteur: list[int] = []
        self.total: list[int] = []

    def demarrer(self, pid_moteur: int | None) -> None:
        self._pid_moteur = pid_moteur
        self._fil = threading.Thread(target=self._boucle, daemon=True)
        self._fil.start()

    def _echantillon(self) -> None:
        rss_app = self._mesure.rss_octets(self._pid_app)
        rss_moteur = (
            self._mesure.rss_octets(self._pid_moteur) if self._pid_moteur is not None else None
        )
        if rss_app is not None:
            self.app.append(rss_app)
        if rss_moteur is not None:
            self.moteur.append(rss_moteur)
        # Pic simultané : somme d'un même échantillon (et non somme des pics de chaque série).
        self.total.append((rss_app or 0) + (rss_moteur or 0))

    def _boucle(self) -> None:
        self._echantillon()
        while not self._arret.wait(INTERVALLE_S):
            self._echantillon()

    def arreter(self) -> None:
        """Arrête le fil puis prend un dernier échantillon (après le `join`) ; idempotent."""
        if self._fil is None or self._arret.is_set():
            return
        self._arret.set()
        self._fil.join(timeout=2.0)
        self._echantillon()

    def pic_app_o(self) -> int:
        return max(self.app, default=0)

    def pic_moteur_o(self) -> int:
        return max(self.moteur, default=0)

    def pic_total_o(self) -> int:
        return max(self.total, default=0)


def _top(rapport: Rapport) -> tuple[int, int, int]:
    """`top1`, `top3`, `etiquetees` : comparaison de `constat_attendu` aux candidats triés."""
    top1 = top3 = etiquetees = 0
    for element in (*rapport.fiches, *rapport.ecartees):
        constat_attendu = (
            element.tracabilite.constat_attendu
            if isinstance(element, Fiche)
            else element.constat_attendu
        )
        if constat_attendu is None:
            continue
        candidats: list[Candidat] = (
            element.tracabilite.candidats if isinstance(element, Fiche) else element.candidats
        )
        etiquetees += 1
        ids = [c.id for c in candidats]
        if ids[:1] == [constat_attendu]:
            top1 += 1
        if constat_attendu in ids[:3]:
            top3 += 1
    return top1, top3, etiquetees


def _recopie(
    fiches: list[Fiche], catalogue: Catalogue, langue: Langue
) -> tuple[float | None, dict[str, float | None], int]:
    """Recopie par rubrique et moyenne globale [revue A29] ; replis exclus et comptés à part.

    `difflib.SequenceMatcher(None, texte_fiche, texte_catalogue).ratio()`, `autojunk` par
    défaut, sur le texte brut de chaque fiche (celui de `fiches.json`), comparé au texte du
    constat réellement rattaché (`tracabilite.constat_id`) dans la langue du lot.
    """
    valeurs_rubrique: dict[str, list[float]] = {r: [] for r in RUBRIQUES}
    replis = 0
    for fiche in fiches:
        if any(motif.code in _MOTIFS_REPLI for motif in fiche.motifs):
            replis += 1
            continue
        textes = catalogue.obtenir(fiche.tracabilite.constat_id).textes(langue)
        for rubrique in RUBRIQUES:
            ratio = difflib.SequenceMatcher(
                None, getattr(fiche, rubrique), getattr(textes, rubrique)
            ).ratio()
            valeurs_rubrique[rubrique].append(ratio)
    recopie_par_rubrique = {
        rubrique: statistics.mean(valeurs) if valeurs else None
        for rubrique, valeurs in valeurs_rubrique.items()
    }
    toutes = [valeur for valeurs in valeurs_rubrique.values() for valeur in valeurs]
    recopie = statistics.mean(toutes) if toutes else None
    return recopie, recopie_par_rubrique, replis


def executer_banc(
    dossier: Path,
    config: Configuration,
    modele: str | None = None,
    langue: Langue | None = None,
    seed: int | None = None,
) -> Path:
    """Exécute un lot instrumenté ; écrit et affiche `banc.json` ; renvoie son chemin (§29).

    `seed` remplace `config.moteur.seed` par copie de configuration [revue A31] ; défaut : la
    configuration.
    """
    config_banc = config
    if seed is not None:
        config_banc = config.model_copy(
            update={"moteur": config.moteur.model_copy(update={"seed": seed})}
        )
    seed_effective = config_banc.moteur.seed
    catalogue = composition.creer_catalogue(config_banc)
    mesure = composition.creer_mesure_memoire()
    echantillonneur = _Echantillonneur(mesure, os.getpid())
    durees: list[tuple[str, float]] = []
    info: dict[str, str] = {}
    total_notes: list[int] = []

    def abonne(evenement: EvenementLot) -> None:
        if evenement.type == TypeEvenement.LOT_DEMARRE:
            pid_moteur = evenement.details.get("pid_moteur")
            echantillonneur.demarrer(pid_moteur if isinstance(pid_moteur, int) else None)
            info["modele"] = str(evenement.details.get("modele", ""))
            info["langue"] = str(evenement.details.get("langue", ""))
            total_notes.append(evenement.total)
        elif evenement.type in (
            TypeEvenement.FICHE_TERMINEE,
            TypeEvenement.FICHE_NON_TRAITEE,
            TypeEvenement.FICHE_NON_RATTACHEE,
        ):
            if evenement.note is not None and evenement.duree_s is not None:
                durees.append((evenement.note, evenement.duree_s))
        elif evenement.type in (TypeEvenement.LOT_TERMINE, TypeEvenement.LOT_ECHOUE):
            echantillonneur.arreter()

    try:
        resultat = executer_lot(
            RequeteLot(dossier=dossier, modele=modele, langue=langue), config_banc, abonne
        )
    finally:
        # Filet si `lot_termine`/`lot_echoue` n'a pas atteint l'abonné (écriture du journal en
        # échec avant l'appel de l'abonné) : le fil d'échantillonnage ne survit pas au lot.
        echantillonneur.arreter()

    top1, top3, etiquetees = _top(resultat.rapport)
    valeurs_durees = [duree for _, duree in durees]
    pic_app = echantillonneur.pic_app_o()
    pic_moteur = echantillonneur.pic_moteur_o()
    pic_total = echantillonneur.pic_total_o()
    fiches = resultat.rapport.fiches
    langue_effective: Langue = info.get("langue") or "fr"  # type: ignore[assignment]
    recopie, recopie_par_rubrique, replis = _recopie(fiches, catalogue, langue_effective)
    ok = sum(1 for fiche in fiches if fiche.statut == Statut.OK)
    a_revoir = len(fiches) - ok
    motifs: Counter[str] = Counter()
    for fiche in fiches:
        for motif in fiche.motifs:
            motifs[motif.code.value] += 1
    banc = {
        "id_lot": resultat.id_lot,
        "modele": info.get("modele", ""),
        "langue": langue_effective,
        "fiches": [{"note": note, "duree_s": duree} for note, duree in durees],
        "duree_mediane_s": statistics.median(valeurs_durees) if valeurs_durees else 0.0,
        "duree_max_s": max(valeurs_durees, default=0.0),
        "pic_rss_app_o": pic_app,
        "pic_rss_moteur_o": pic_moteur,
        "pic_rss_total_o": pic_total,
        "top1": top1,
        "top3": top3,
        "etiquetees": etiquetees,
        "ok": ok,
        "a_revoir": a_revoir,
        "recopie": recopie,
        "recopie_par_rubrique": recopie_par_rubrique,
        "replis": replis,
        "seed": seed_effective,
        "motifs": dict(motifs),
    }
    chemin = resultat.dossier_sortie / FICHIER
    chemin.write_text(json.dumps(banc, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        f"banc {resultat.id_lot} (modèle {banc['modele']}) : "
        f"{len(durees)} fiche(s) traitée(s), "
        f"durée médiane {banc['duree_mediane_s']} s, max {banc['duree_max_s']} s"
    )
    print(f"pic RSS app {pic_app} o, moteur {pic_moteur} o, total {banc['pic_rss_total_o']} o")
    print(f"top1 {top1}/{etiquetees}, top3 {top3}/{etiquetees} ; rapport : {chemin}")
    recopie_txt = "null" if recopie is None else f"{recopie:.2f}"
    rubriques_txt = " ".join(
        f"{rubrique} {'null' if valeur is None else f'{valeur:.2f}'}"
        for rubrique, valeur in recopie_par_rubrique.items()
    )
    # Dénominateur : notes du lot (une note écartée ne gonfle pas le taux ok affiché, CAP-7).
    total = total_notes[0] if total_notes else len(fiches)
    print(f"ok {ok}/{total}, recopie {recopie_txt} ({rubriques_txt})")
    return chemin
