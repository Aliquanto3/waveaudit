"""Banc de mesure de bout en bout (contrats §20, §29, CAP-12), faux moteur et `MesureMemoire`
factice."""

import difflib
import json
import os
import shutil
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


def _vers(config, fm):
    return config.model_copy(
        update={"moteur": config.moteur.model_copy(update={"base_url": fm.base_url})}
    )


def _dossier_une_note(tmp_path, nom="01-xss-reflechi.md"):
    dossier = tmp_path / "notes"
    dossier.mkdir()
    shutil.copy(DEMO / nom, dossier / nom)
    return dossier


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
        "langue",
        "fiches",
        "duree_mediane_s",
        "duree_max_s",
        "pic_rss_app_o",
        "pic_rss_moteur_o",
        "pic_rss_total_o",
        "top1",
        "top3",
        "etiquetees",
        "ok",
        "a_revoir",
        "recopie",
        "recopie_par_rubrique",
        "replis",
        "seed",
        "motifs",
    }
    assert len(donnees["fiches"]) == total
    assert donnees["duree_max_s"] >= donnees["duree_mediane_s"] >= 0.0
    assert donnees["pic_rss_app_o"] == 123_456_789
    # mode externe (config_test) : pid_moteur est None, donc pas d'échantillon moteur.
    assert donnees["pic_rss_moteur_o"] == 0
    assert donnees["pic_rss_total_o"] == donnees["pic_rss_app_o"]
    assert 0 <= donnees["top1"] <= donnees["top3"] <= donnees["etiquetees"] <= total
    assert donnees["langue"] == "fr"
    assert donnees["ok"] + donnees["a_revoir"] <= len(donnees["fiches"])
    assert donnees["replis"] <= donnees["a_revoir"]
    assert donnees["seed"] == config_test.moteur.seed
    assert set(donnees["recopie_par_rubrique"]) == {
        "titre",
        "description",
        "impact",
        "recommandation",
    }


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


def test_banc_echantillonnage_arrete_si_lot_echoue_n_atteint_pas_l_abonne(config_test, monkeypatch):
    """Exception sortie de `executer_lot` sans `lot_echoue` reçu (journal en échec) : le banc
    arrête quand même son fil d'échantillonnage."""
    mesure = _MesureFactice(valeurs={os.getpid(): 10})

    def faux_executer_lot(requete, config, abonne):
        abonne(
            EvenementLot(
                type=TypeEvenement.LOT_DEMARRE,
                horodatage=datetime.now().astimezone(),
                index=None,
                total=0,
                note=None,
                statut=None,
                duree_s=None,
                details={"id_lot": "x", "modele": "m", "pid_moteur": None},
            )
        )
        raise OSError("disque plein")

    monkeypatch.setattr(composition, "creer_mesure_memoire", lambda: mesure)
    monkeypatch.setattr(banc, "executer_lot", faux_executer_lot)
    monkeypatch.setattr(banc, "INTERVALLE_S", 0.05)

    with pytest.raises(OSError, match="disque plein"):
        banc.executer_banc(DEMO, config_test, None)

    appels_apres = mesure.appels
    time.sleep(0.2)
    assert mesure.appels == appels_apres


def test_pic_total_est_le_pic_simultane():
    """`pic_rss_total_o` : maximum de la somme app + moteur d'un même échantillon."""

    class _Mesure:
        def __init__(self) -> None:
            self.series = {1: iter([100, 10]), 2: iter([10, 50])}

        def rss_octets(self, pid: int) -> int | None:
            return next(self.series[pid])

    echantillonneur = banc._Echantillonneur(_Mesure(), 1)
    echantillonneur._pid_moteur = 2
    echantillonneur._echantillon()
    echantillonneur._echantillon()

    assert (echantillonneur.pic_app_o(), echantillonneur.pic_moteur_o()) == (100, 50)
    assert echantillonneur.pic_total_o() == 110  # et non 150 (pics à deux instants différents)


def test_recopie_sans_fiche_est_null():
    """[v2] Aucune fiche mesurable : `recopie` et chaque rubrique valent `None` (§29)."""
    catalogue = object()  # jamais consulté : aucune fiche à mesurer

    recopie, recopie_par_rubrique, replis = banc._recopie([], catalogue, "fr")

    assert recopie is None
    assert replis == 0
    assert recopie_par_rubrique == {
        "titre": None,
        "description": None,
        "impact": None,
        "recommandation": None,
    }


def test_repli_exclu_de_la_recopie_banc_json(config_test, faux_moteur, tmp_path):
    """[v2] Une fiche en repli (`repli_sortie_invalide`) est comptée dans `replis`, jamais dans
    la recopie ; seule fiche du lot -> `recopie` `null` (contrats §29, revue A29)."""
    dossier = _dossier_une_note(tmp_path)
    fm = faux_moteur("json_invalide")
    config = _vers(config_test, fm)

    chemin = banc.executer_banc(dossier, config, None)

    donnees = json.loads(chemin.read_text(encoding="utf-8"))
    assert donnees["replis"] == 1
    assert donnees["recopie"] is None
    assert all(valeur is None for valeur in donnees["recopie_par_rubrique"].values())


def test_recopie_nominale_proche_de_un(config_test, tmp_path):
    """[v2] Faux moteur nominal ("[adapté] " + texte du constat) : recopie proche de 1 (§29)."""
    dossier = _dossier_une_note(tmp_path)

    chemin = banc.executer_banc(dossier, config_test, None)

    donnees = json.loads(chemin.read_text(encoding="utf-8"))
    assert donnees["replis"] == 0
    assert donnees["recopie"] is not None
    assert donnees["recopie"] > 0.8
    assert all(valeur > 0.8 for valeur in donnees["recopie_par_rubrique"].values())


def test_langue_en_comparee_aux_textes_anglais(config_test, faux_moteur, tmp_path):
    """[v2] Lot en anglais : la recopie compare au texte anglais du constat, pas au français."""
    dossier = _dossier_une_note(tmp_path)
    fm = faux_moteur()
    config = _vers(config_test, fm)

    chemin = banc.executer_banc(dossier, config, None, "en")

    donnees = json.loads(chemin.read_text(encoding="utf-8"))
    assert donnees["langue"] == "en"
    fiches = json.loads((chemin.parent / "fiches.json").read_text(encoding="utf-8"))["fiches"]
    (fiche,) = fiches
    catalogue = composition.creer_catalogue(config)
    constat = catalogue.obtenir(fiche["tracabilite"]["constat_id"])
    ratio_en = difflib.SequenceMatcher(None, fiche["titre"], constat.textes("en").titre).ratio()
    ratio_fr = difflib.SequenceMatcher(None, fiche["titre"], constat.textes("fr").titre).ratio()
    assert ratio_en > ratio_fr
    assert donnees["recopie_par_rubrique"]["titre"] == pytest.approx(ratio_en)


def test_recopie_null_sans_fiche_mesurable(config_test, faux_moteur, tmp_path):
    """[v2] Lot sans fiche (toutes les notes en repli) : `recopie` reste `null` (§29)."""
    dossier = tmp_path / "notes"
    dossier.mkdir()
    shutil.copy(DEMO / "01-xss-reflechi.md", dossier / "01-xss-reflechi.md")
    shutil.copy(DEMO / "02-xss-stocke.md", dossier / "02-xss-stocke.md")
    fm = faux_moteur("json_invalide")
    config = _vers(config_test, fm)

    chemin = banc.executer_banc(dossier, config, None)

    donnees = json.loads(chemin.read_text(encoding="utf-8"))
    assert donnees["replis"] == 2
    assert donnees["recopie"] is None


def test_seed_consignee_et_recue_par_le_faux_moteur(config_test, faux_moteur, tmp_path):
    """[v2] `--seed` remplace `config.moteur.seed` et atteint le faux moteur (revue A31)."""
    dossier = _dossier_une_note(tmp_path)
    fm = faux_moteur()
    config = _vers(config_test, fm)

    chemin = banc.executer_banc(dossier, config, None, None, 142)

    donnees = json.loads(chemin.read_text(encoding="utf-8"))
    assert donnees["seed"] == 142
    assert config_test.moteur.seed != 142  # config inchangée : copie, pas mutation
    assert all(requete["seed"] == 142 for requete in fm.requetes)


def test_seed_defaut_est_celle_de_la_configuration(config_test, tmp_path):
    """Sans `--seed`, la seed effective reste celle de la configuration (contrats §29)."""
    dossier = _dossier_une_note(tmp_path)

    chemin = banc.executer_banc(dossier, config_test, None)

    donnees = json.loads(chemin.read_text(encoding="utf-8"))
    assert donnees["seed"] == config_test.moteur.seed
