"""Pipeline incident : récit, repli, assemblage (contrats §21, CAP-5), faux moteur."""

from collections.abc import Callable, Iterator
from datetime import timedelta

import pytest

from tests.faux_moteur import FauxMoteur
from tests.incident_outils import HORODATAGE, detection, evenement, recit, regle
from waveaudit.adaptateurs.moteur_openai import MoteurOpenAI
from waveaudit.domaine.configuration import Configuration
from waveaudit.domaine.incident import LectureJournaux, LigneIgnoree
from waveaudit.domaine.indicateurs import extraire
from waveaudit.domaine.modeles import CodeMotif, Statut
from waveaudit.workflows.incident import pipeline

Traiter = Callable[..., tuple]


@pytest.fixture
def traiter(
    config_test: Configuration, faux_moteur: Callable[..., FauxMoteur]
) -> Iterator[Traiter]:
    ouverts: list[MoteurOpenAI] = []

    def fabrique(scenario: str = "nominal", d=None, r=None):
        fm = faux_moteur(scenario)
        moteur = MoteurOpenAI(fm.base_url, "modele-test", timeout_s=1.0)
        ouverts.append(moteur)
        resultat = pipeline.traiter_detection(
            d or detection(), r or regle(), moteur, "PREFIXE", config_test
        )
        return resultat, fm

    yield fabrique
    for moteur in ouverts:
        moteur.fermer()


def _codes(r) -> list[CodeMotif]:
    return [m.code for m in r.motifs]


def test_nominal_recit_adapte_et_indicateurs_remplis(traiter, config_test):
    resultat, fm = traiter()
    r = regle()
    assert resultat.statut == Statut.OK and resultat.motifs == []
    assert resultat.titre == "[adapté] " + r.titre
    assert resultat.recit == "[adapté] " + r.description
    assert resultat.references == r.references and resultat.regle_titre == r.titre
    assert resultat.detection.indicateurs == extraire(resultat.detection.evenements)
    assert resultat.detection.indicateurs
    assert len(fm.requetes) == 1
    requete = fm.requetes[0]
    assert requete["max_tokens"] == config_test.incident.max_tokens
    assert requete["messages"][0]["content"].startswith("PREFIXE\n")
    assert "<regle>" in requete["messages"][-1]["content"]


def test_references_inventees_retirees_et_signalees(traiter):
    resultat, _ = traiter("references_inventees")
    assert resultat.statut == Statut.A_REVOIR
    assert sorted(_codes(resultat)) == sorted(
        [CodeMotif.REFERENCE_RETIREE] * 2 + [CodeMotif.INDICATEUR_RETIRE] * 2
    )
    assert {m.detail for m in resultat.motifs} == {"T9999", "T1110.999", "203.0.113.254", "0f" * 32}
    for jeton in ("T9999", "T1110.999", "203.0.113.254", "0f" * 32):
        assert jeton not in resultat.recit


def test_json_invalide_une_fois_puis_succes(traiter):
    resultat, fm = traiter("json_invalide_une_fois")
    assert resultat.statut == Statut.OK
    assert len(fm.requetes) == 2
    assert fm.requetes[0]["messages"] == fm.requetes[1]["messages"]
    assert fm.requetes[0]["seed"] == 42 and fm.requetes[1]["seed"] == 43


def test_json_invalide_deux_fois_repli(traiter):
    resultat, fm = traiter("json_invalide")
    r = regle()
    assert len(fm.requetes) == 2
    assert fm.requetes[0]["seed"] == 42 and fm.requetes[1]["seed"] == 43
    assert _codes(resultat) == [CodeMotif.REPLI_SORTIE_INVALIDE]
    assert resultat.statut == Statut.A_REVOIR
    assert (resultat.titre, resultat.recit, resultat.impact, resultat.recommandation) == (
        r.titre,
        r.description,
        r.impact,
        r.recommandation,
    )
    assert resultat.detection.indicateurs


@pytest.mark.parametrize("scenario", ["erreur_500", "injoignable"])
def test_moteur_en_echec_repli_immediat(traiter, scenario):
    resultat, fm = traiter(scenario)
    assert _codes(resultat) == [CodeMotif.REPLI_MOTEUR]
    assert resultat.statut == Statut.A_REVOIR
    assert resultat.recit == regle().description
    assert len(fm.requetes) == (1 if scenario == "erreur_500" else 0)


def _lecture(**surcharges) -> LectureJournaux:
    donnees: dict = {"evenements": [], "ignorees": [], "fichiers": {"auth.log": 3}}
    return LectureJournaux.model_validate(donnees | surcharges)


def test_assembler_sans_detection():
    ignoree = LigneIgnoree(fichier="auth.log", ligne=2, raison="illisible")
    rapport = pipeline.assembler_rapport(_lecture(ignorees=[ignoree]), [], {})
    assert rapport.debut is None and rapport.fin is None
    assert rapport.recits == [] and rapport.indicateurs == [] and rapport.actifs == []
    assert rapport.recommandations == []
    assert rapport.sources == {"auth.log": 3} and rapport.ignorees == [ignoree]


def test_assembler_union_actifs_recommandations():
    e1 = evenement(ligne=1, hote="bastion02")
    e2 = evenement(ligne=2, horodatage=HORODATAGE + timedelta(seconds=30), hote="BASTION01")
    e3 = evenement(
        ligne=3,
        horodatage=HORODATAGE + timedelta(minutes=5),
        hote="Alpha",
        message="Failed password for root from 198.51.100.7 port 1 ssh2",
        champs={"utilisateur": "root", "ip": "198.51.100.7", "port": "1"},
    )
    autre = regle(
        id="INC-LIN-SUDO-SHELL",
        recommandation="Restreindre sudo aux commandes nécessaires et journaliser.",
        agregation=None,
    )
    r1 = recit(detection=detection(evenements=[e1, e2]))
    r2 = recit(detection=detection(regle_id=autre.id, evenements=[e2, e3]))
    r3 = recit(detection=detection(evenements=[e3]))
    regles = {regle().id: regle(), autre.id: autre}
    rapport = pipeline.assembler_rapport(_lecture(), [r1, r2, r3], regles)
    assert rapport.recits == [r1, r2, r3]
    assert rapport.debut == e1.horodatage and rapport.fin == e3.horodatage
    assert rapport.indicateurs == extraire([e1, e2, e3])
    assert rapport.actifs == ["Alpha", "BASTION01", "bastion02"]
    assert rapport.recommandations == [regle().recommandation, autre.recommandation]


def test_actifs_ordre_total_meme_graphie_casefold():
    d1 = detection(evenements=[evenement(hote="hote1")])
    d2 = detection(evenements=[evenement(ligne=2, hote="HOTE1")])
    rapport = pipeline.assembler_rapport(
        _lecture(), [recit(detection=d1), recit(detection=d2)], {regle().id: regle()}
    )
    assert rapport.actifs == ["HOTE1", "hote1"]
