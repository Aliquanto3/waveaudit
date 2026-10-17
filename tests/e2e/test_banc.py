"""Banc de mesure de bout en bout (contrats §20, CAP-12), faux moteur et `MesureMemoire` factice."""

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime

import pytest

from waveaudit.application import banc, composition
from waveaudit.application.config import racine_projet
from waveaudit.domaine.erreurs import MoteurInjoignable
from waveaudit.domaine.modeles import (
    Candidat,
    Cvss,
    EntreeEcartee,
    EvenementLot,
    Fiche,
    Motif,
    Rapport,
    Statut,
    Tracabilite,
    TypeEvenement,
)

DEMO = racine_projet() / "donnees" / "demo" / "notes"


@dataclass
class _MesureFactice:
    """`MesureMemoire` factice : une valeur constante par pid, nombre d'appels tracé."""

    valeurs: dict[int, int]
    appels: int = field(default=0)

    def rss_octets(self, pid: int) -> int | None:
        self.appels += 1
        return self.valeurs.get(pid)


def _cvss() -> Cvss:
    vecteur = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N"
    return Cvss(vecteur=vecteur, score=9.0, severite="critique")


def _fiche(constat_attendu: str | None, candidats: list[str]) -> Fiche:
    return Fiche(
        titre="t",
        description="d",
        impact="i",
        recommandation="r",
        cvss=_cvss(),
        references=[],
        statut=Statut.OK,
        motifs=[],
        tracabilite=Tracabilite(
            note="n.md",
            constat_id=candidats[0],
            candidats=[Candidat(id=c, score=1.0) for c in candidats],
            constat_attendu=constat_attendu,
        ),
    )


def _ecartee(constat_attendu: str | None, candidats: list[str]) -> EntreeEcartee:
    return EntreeEcartee(
        note="n.md",
        statut=Statut.NON_RATTACHEE,
        motif=Motif(code="aucun_constat", detail="x"),
        candidats=[Candidat(id=c, score=1.0) for c in candidats],
        constat_attendu=constat_attendu,
    )


def test_top_depuis_tracabilite_et_entrees_ecartees():
    rapport = Rapport(
        fiches=[
            _fiche("WEB-A", ["WEB-A", "WEB-B", "WEB-C"]),  # top1 et top3
            _fiche("WEB-B", ["WEB-A", "WEB-B", "WEB-C"]),  # top3 seulement
            _fiche("WEB-D", ["WEB-A", "WEB-B", "WEB-C"]),  # ni l'un ni l'autre
            _fiche(None, ["WEB-A"]),  # pas étiquetée : exclue du dénominateur
        ],
        ecartees=[
            _ecartee("WEB-E", ["WEB-E"]),  # top1 et top3
        ],
    )

    top1, top3, etiquetees = banc._top(rapport)

    assert (top1, top3, etiquetees) == (2, 3, 4)


def test_banc_json_nominal(config_test, monkeypatch):
    mesure = _MesureFactice(valeurs={os.getpid(): 123_456_789})
    monkeypatch.setattr(composition, "creer_mesure_memoire", lambda: mesure)

    chemin = banc.executer_banc(DEMO, config_test, None)

    assert chemin.name == "banc.json"
    donnees = json.loads(chemin.read_text(encoding="utf-8"))
    total = len(list(DEMO.glob("*.md"))) + len(list(DEMO.glob("*.txt")))
    assert set(donnees) == {
        "id_lot",
        "modele",
        "fiches",
        "duree_mediane_s",
        "duree_max_s",
        "pic_rss_app_o",
        "pic_rss_moteur_o",
        "pic_rss_total_o",
        "top1",
        "top3",
        "etiquetees",
    }
    assert len(donnees["fiches"]) == total
    assert donnees["duree_max_s"] >= donnees["duree_mediane_s"] >= 0.0
    assert donnees["pic_rss_app_o"] == 123_456_789
    # mode externe (config_test) : pid_moteur est None, donc pas d'échantillon moteur.
    assert donnees["pic_rss_moteur_o"] == 0
    assert donnees["pic_rss_total_o"] == donnees["pic_rss_app_o"]
    assert 0 <= donnees["top1"] <= donnees["top3"] <= donnees["etiquetees"] <= total


def test_banc_echantillonnage_arrete_a_lot_echoue(config_test, monkeypatch):
    """`lot_demarre` puis `lot_echoue` (sans fiche traitée) : le fil d'échantillonnage démarre
    puis s'arrête bel et bien — on ne le laisse pas tourner après l'échec du lot."""
    mesure = _MesureFactice(valeurs={os.getpid(): 10, 4242: 20})
    maintenant = datetime.now().astimezone()

    def faux_executer_lot(requete, config, abonne):
        abonne(
            EvenementLot(
                type=TypeEvenement.LOT_DEMARRE,
                horodatage=maintenant,
                index=None,
                total=0,
                note=None,
                statut=None,
                duree_s=None,
                details={"id_lot": "x", "modele": "m", "pid_moteur": 4242},
            )
        )
        abonne(
            EvenementLot(
                type=TypeEvenement.LOT_ECHOUE,
                horodatage=maintenant,
                index=None,
                total=0,
                note=None,
                statut=None,
                duree_s=None,
                details={},
            )
        )
        raise MoteurInjoignable("x")

    monkeypatch.setattr(composition, "creer_mesure_memoire", lambda: mesure)
    monkeypatch.setattr(banc, "executer_lot", faux_executer_lot)

    with pytest.raises(MoteurInjoignable):
        banc.executer_banc(DEMO, config_test, None)

    assert mesure.appels >= 2  # au moins un échantillon app et un échantillon moteur
    appels_apres = mesure.appels
    time.sleep(0.3)
    assert mesure.appels == appels_apres  # le fil d'échantillonnage est bien arrêté
