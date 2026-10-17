"""Fixture des événements canoniques (`tests/donnees/incident/canoniques.yaml`, C1)."""

import json
from pathlib import Path

import pytest
import yaml

from waveaudit.domaine.incident import IDS_REGLES_MINIMAUX, Evenement

FIXTURE = Path(__file__).parents[1] / "donnees" / "incident" / "canoniques.yaml"
FICHIERS = {"security.json", "system.json", "sysmon.csv", "auth.log"}
ENTREES = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
CLES = {"id", "fichier", "brut", "ligne", "evenement", "regles"}


def _construire(entree: dict) -> Evenement:
    return Evenement.model_validate(
        entree["evenement"] | {"fichier": entree["fichier"], "ligne": entree["ligne"]}
    )


def test_forme_des_entrees():
    assert isinstance(ENTREES, list)
    assert len({e["id"] for e in ENTREES}) == len(ENTREES)
    for entree in ENTREES:
        assert set(entree) == CLES, entree["id"]
        assert entree["fichier"] in FICHIERS, entree["id"]
        assert isinstance(entree["brut"], str) and entree["brut"].endswith("\n")


@pytest.mark.parametrize("entree", ENTREES, ids=[e["id"] for e in ENTREES])
def test_evenement_valide(entree):
    evenement = _construire(entree)
    assert evenement.horodatage.utcoffset() is not None
    assert evenement.cle == (entree["fichier"], entree["ligne"])
    assert set(entree["regles"]) <= set(IDS_REGLES_MINIMAUX)
    assert len(entree["regles"]) == len(set(entree["regles"]))


@pytest.mark.parametrize("entree", ENTREES, ids=[e["id"] for e in ENTREES])
def test_brut_minimal(entree):
    brut, fichier = entree["brut"], entree["fichier"]
    if fichier.endswith(".json"):
        objets = json.loads(brut)
        assert isinstance(objets, list) and len(objets) == 1 and entree["ligne"] == 1
        assert isinstance(objets[0]["Data"], dict)
    elif fichier.endswith(".csv"):
        assert len(brut.splitlines()) == 2 and entree["ligne"] == 2
    else:
        assert len(brut.splitlines()) == 1 and entree["ligne"] == 1


def test_chronologie_complete_et_regles_couvertes():
    chrono = [e for e in ENTREES if e["id"].startswith("chrono-")]
    assert len(chrono) == 17
    assert len([e for e in ENTREES if e["id"].startswith("benin-")]) >= 10
    couvertes = {r for e in ENTREES for r in e["regles"]}
    assert couvertes == set(IDS_REGLES_MINIMAUX)
    assert {r for e in chrono for r in e["regles"]} == set(IDS_REGLES_MINIMAUX)


def test_valeurs_reservees_au_faux_moteur_absentes():
    texte = FIXTURE.read_text(encoding="utf-8")
    for valeur in ("203.0.113.254", "0f" * 32, "T9999", "T1110.999"):
        assert valeur not in texte
