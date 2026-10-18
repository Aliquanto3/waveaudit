"""Garde-fou langue dans un lot anglais (contrats §6 étape 6, §23 ; revue A18, CAP-4)."""

from pathlib import Path

from tests.faux_moteur import FauxMoteur
from waveaudit.adaptateurs.catalogue_yaml import CatalogueYaml
from waveaudit.adaptateurs.moteur_openai import MoteurOpenAI
from waveaudit.adaptateurs.notes_fichiers import NotesFichiers
from waveaudit.domaine.configuration import Configuration
from waveaudit.domaine.modeles import CodeMotif, ConstatType, Fiche, Note, Rapport, Statut
from waveaudit.domaine.ports import Ports
from waveaudit.workflows.registre import REGISTRE

RACINE = Path(__file__).resolve().parents[2]
NOTE_XSS = "01-xss-reflechi.md"


class _ExporteurMemoire:
    def exporter(self, rapport: Rapport, chemin: Path) -> None:  # pragma: no cover
        raise AssertionError("le workflow n'exporte jamais")


class _CatalogueMemoire:
    def __init__(self, constats: list[ConstatType]) -> None:
        self._constats = {c.id: c for c in constats}

    def constats(self) -> list[ConstatType]:
        return sorted(self._constats.values(), key=lambda c: c.id)

    def obtenir(self, id: str) -> ConstatType:
        return self._constats[id]


def _note() -> Note:
    notes = NotesFichiers().lire(RACINE / "donnees" / "demo" / "notes")
    element = next(e for e in notes if e.fichier == NOTE_XSS)
    assert isinstance(element, Note)
    return element


def _fabriquer_lot_en(config_test: Configuration, fm: FauxMoteur) -> tuple[object, MoteurOpenAI]:
    constats = CatalogueYaml(RACINE / "donnees" / "catalogue").constats()
    config = config_test.model_copy(
        update={
            "moteur": config_test.moteur.model_copy(update={"base_url": fm.base_url}),
            "fiches": config_test.fiches.model_copy(update={"langue": "en"}),
        }
    )
    moteur = MoteurOpenAI(fm.base_url, "modele-test", timeout_s=config.moteur.timeout_s)
    ports = Ports(
        moteur=moteur,
        catalogue=_CatalogueMemoire(constats),
        source_notes=None,  # non utilisé : `traiter` est appelé directement sur la note
        exporteur=_ExporteurMemoire(),
        prefixe_systeme="",
    )
    workflow = REGISTRE["fiches"](config, ports)
    return workflow, moteur


def test_fiche_francaise_dans_un_lot_en(config_test, faux_moteur) -> None:
    """Un récit français dans un lot `en` reçoit le motif `langue` et passe à `a_revoir`."""
    fm = faux_moteur("langue_francaise")
    workflow, moteur = _fabriquer_lot_en(config_test, fm)
    try:
        resultat = workflow.traiter(_note())
    finally:
        moteur.fermer()

    assert isinstance(resultat, Fiche)
    assert resultat.statut == Statut.A_REVOIR
    assert CodeMotif.LANGUE in [m.code for m in resultat.motifs]


def test_fiche_anglaise_dans_un_lot_en_ok(config_test, faux_moteur) -> None:
    """Un récit déjà anglais dans un lot `en` ne déclenche pas le motif `langue`."""
    fm = faux_moteur("langue_anglaise")
    workflow, moteur = _fabriquer_lot_en(config_test, fm)
    try:
        resultat = workflow.traiter(_note())
    finally:
        moteur.fermer()

    assert isinstance(resultat, Fiche)
    assert resultat.statut == Statut.OK
    assert CodeMotif.LANGUE not in [m.code for m in resultat.motifs]
