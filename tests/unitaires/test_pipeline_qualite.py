"""Pipeline `fiches` × garde-fous de qualité (contrats §6 v2, CAP-3/CAP-4), faux moteur.

Fichier séparé de `test_pipeline.py` (story Q1, en parallèle) pour éviter toute collision.
"""

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from tests.faux_moteur import FauxMoteur
from waveaudit.adaptateurs.catalogue_yaml import CatalogueYaml
from waveaudit.adaptateurs.moteur_openai import MoteurOpenAI
from waveaudit.adaptateurs.notes_fichiers import NotesFichiers
from waveaudit.application.config import racine_projet
from waveaudit.domaine.configuration import Configuration
from waveaudit.domaine.erreurs import EntreeInvalide
from waveaudit.domaine.modeles import (
    CodeMotif,
    ConstatType,
    Fiche,
    Note,
    NoteInvalide,
    Rapport,
    Statut,
)
from waveaudit.domaine.ports import Ports
from waveaudit.workflows.fiches import pipeline
from waveaudit.workflows.registre import REGISTRE

RACINE = racine_projet()
NOTES_DEMO = RACINE / "donnees" / "demo" / "notes"
NOTE_XSS = "01-xss-reflechi.md"


class CatalogueMemoire:
    def __init__(self, constats: list[ConstatType]) -> None:
        self._constats = {c.id: c for c in constats}

    def constats(self) -> list[ConstatType]:
        return sorted(self._constats.values(), key=lambda c: c.id)

    def obtenir(self, id: str) -> ConstatType:
        try:
            return self._constats[id]
        except KeyError as erreur:
            raise EntreeInvalide(id) from erreur


class SourceMemoire:
    def __init__(self, elements: list[Note | NoteInvalide]) -> None:
        self.elements = elements

    def lire(self, dossier: Path) -> list[Note | NoteInvalide]:
        return list(self.elements)


class ExporteurMemoire:
    def exporter(self, rapport: Rapport, chemin: Path) -> None:  # pragma: no cover
        raise AssertionError("le workflow n'exporte jamais")


@pytest.fixture(scope="module")
def constats() -> list[ConstatType]:
    return CatalogueYaml(RACINE / "donnees" / "catalogue").constats()


def _note(nom: str) -> Note:
    element = next(e for e in NotesFichiers().lire(NOTES_DEMO) if e.fichier == nom)
    assert isinstance(element, Note)
    return element


@pytest.fixture
def moteurs() -> Iterator[list[MoteurOpenAI]]:
    ouverts: list[MoteurOpenAI] = []
    yield ouverts
    for moteur in ouverts:
        moteur.fermer()


@pytest.fixture
def fabriquer(
    config_test: Configuration,
    faux_moteur: Callable[..., FauxMoteur],
    constats: list[ConstatType],
    moteurs: list[MoteurOpenAI],
) -> Callable[..., tuple[pipeline.WorkflowFiches, FauxMoteur]]:
    def fabrique(scenario: str = "nominal") -> tuple[pipeline.WorkflowFiches, FauxMoteur]:
        fm = faux_moteur(scenario)
        config = config_test.model_copy(
            update={"moteur": config_test.moteur.model_copy(update={"base_url": fm.base_url})}
        )
        moteur = MoteurOpenAI(fm.base_url, "modele-test", timeout_s=config.moteur.timeout_s)
        moteurs.append(moteur)
        ports = Ports(
            moteur=moteur,
            catalogue=CatalogueMemoire(constats),
            source_notes=SourceMemoire([]),
            exporteur=ExporteurMemoire(),
            prefixe_systeme="",
        )
        workflow = REGISTRE["fiches"](config, ports)
        assert isinstance(workflow, pipeline.WorkflowFiches)
        return workflow, fm

    return fabrique


def _codes(fiche: Fiche) -> list[CodeMotif]:
    return [m.code for m in fiche.motifs]


def test_scenario_repetition_a_revoir(fabriquer) -> None:
    workflow, fm = fabriquer("repetition")
    resultat = workflow.traiter(_note(NOTE_XSS))
    assert isinstance(resultat, Fiche)
    assert resultat.statut == Statut.A_REVOIR
    assert any(
        m.code == CodeMotif.REPETITION and m.detail == "description" for m in resultat.motifs
    )


def test_scenario_langue_anglaise_dans_lot_francais_a_revoir(fabriquer) -> None:
    """Le lot v0.1.0 est en français par défaut (`langue="fr"` non transmise par le pipeline)."""
    workflow, fm = fabriquer("langue_anglaise")
    resultat = workflow.traiter(_note(NOTE_XSS))
    assert isinstance(resultat, Fiche)
    assert resultat.statut == Statut.A_REVOIR
    details = {m.detail for m in resultat.motifs if m.code == CodeMotif.LANGUE}
    assert details == {
        "description : mots-outils en",
        "impact : mots-outils en",
        "recommandation : mots-outils en",
    }


def test_scenario_ecriture_etrangere_a_revoir(fabriquer) -> None:
    workflow, fm = fabriquer("ecriture_etrangere")
    resultat = workflow.traiter(_note(NOTE_XSS))
    assert isinstance(resultat, Fiche)
    assert resultat.statut == Statut.A_REVOIR
    assert any(
        m.code == CodeMotif.LANGUE and m.detail == "description : écriture non latine"
        for m in resultat.motifs
    )


def test_scenario_url_de_la_note_ok(fabriquer) -> None:
    """L'URL citée par le faux moteur depuis la note (`actif`) est gardée, aucun motif."""
    workflow, fm = fabriquer("url_de_la_note")
    resultat = workflow.traiter(_note(NOTE_XSS))
    assert isinstance(resultat, Fiche)
    assert resultat.statut == Statut.OK
    assert resultat.motifs == []
    assert "https://portail.exemple.test/recherche?q=" in resultat.description
