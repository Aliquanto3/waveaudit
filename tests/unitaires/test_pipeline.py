"""Workflow `fiches` : pipeline et prompt (contrats §5, §8 ; AD-4, AD-6, AD-15).

Un vrai `MoteurOpenAI` contre le faux moteur ; catalogue, notes et exporteur en mémoire.
"""

import json
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from tests.faux_moteur import FauxMoteur
from waveaudit.adaptateurs.catalogue_yaml import CatalogueYaml
from waveaudit.adaptateurs.moteur_openai import MoteurOpenAI
from waveaudit.adaptateurs.notes_fichiers import NotesFichiers
from waveaudit.domaine import cvss31
from waveaudit.domaine.configuration import Configuration
from waveaudit.domaine.erreurs import EntreeInvalide
from waveaudit.domaine.modeles import (
    CodeMotif,
    ConstatType,
    EntreeEcartee,
    Fiche,
    Note,
    NoteInvalide,
    Rapport,
    Statut,
)
from waveaudit.domaine.ports import Ports
from waveaudit.workflows.fiches import pipeline, prompt
from waveaudit.workflows.registre import REGISTRE

RACINE = Path(__file__).resolve().parents[2]
NOTES_DEMO = RACINE / "donnees" / "demo" / "notes"
NOTES_TEST = RACINE / "tests" / "donnees" / "notes"


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
        self.lus: list[Path] = []

    def lire(self, dossier: Path) -> list[Note | NoteInvalide]:
        self.lus.append(dossier)
        return list(self.elements)


class ExporteurMemoire:
    def exporter(self, rapport: Rapport, chemin: Path) -> None:  # pragma: no cover
        raise AssertionError("le workflow n'exporte jamais")


@pytest.fixture(scope="module")
def constats() -> list[ConstatType]:
    return CatalogueYaml(RACINE / "donnees" / "catalogue").constats()


def _note(nom: str, dossier: Path = NOTES_DEMO) -> Note:
    element = next(e for e in NotesFichiers().lire(dossier) if e.fichier == nom)
    assert isinstance(element, Note)
    return element


NOTE_XSS = "01-xss-reflechi.md"


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
    def fabrique(
        scenario: str = "nominal", *, prefixe: str = "", **moteur_cfg: object
    ) -> tuple[pipeline.WorkflowFiches, FauxMoteur]:
        fm = faux_moteur(scenario)
        config = config_test.model_copy(
            update={
                "moteur": config_test.moteur.model_copy(
                    update={"base_url": fm.base_url, **moteur_cfg}
                )
            }
        )
        moteur = MoteurOpenAI(fm.base_url, "modele-test", timeout_s=config.moteur.timeout_s)
        moteurs.append(moteur)
        ports = Ports(
            moteur=moteur,
            catalogue=CatalogueMemoire(constats),
            source_notes=SourceMemoire([]),
            exporteur=ExporteurMemoire(),
            prefixe_systeme=prefixe,
        )
        workflow = REGISTRE["fiches"](config, ports)
        assert isinstance(workflow, pipeline.WorkflowFiches)
        return workflow, fm

    return fabrique


def _codes(fiche: Fiche) -> list[CodeMotif]:
    return [m.code for m in fiche.motifs]


def test_nominal_fiche_ok_prefixe_adapte(fabriquer, constats) -> None:
    workflow, fm = fabriquer("nominal")
    resultat = workflow.traiter(_note(NOTE_XSS))

    assert isinstance(resultat, Fiche)
    assert resultat.statut == Statut.OK and resultat.motifs == []
    constat = next(c for c in constats if c.id == resultat.tracabilite.constat_id)
    assert resultat.titre == "[adapté] " + constat.titre
    assert resultat.description == "[adapté] " + constat.description
    assert resultat.references == constat.references
    assert resultat.cvss == cvss31.evaluer(constat.cvss_vecteur)
    assert resultat.tracabilite.note == NOTE_XSS
    # La justesse du rattachement relève de CAP-3 (story 11) : seul le premier candidat compte ici.
    assert resultat.tracabilite.constat_attendu == "WEB-XSS-REFLECHI"
    assert len(resultat.tracabilite.candidats) == 3
    assert resultat.tracabilite.candidats[0].id == constat.id
    assert len(fm.requetes) == 1
    assert fm.requetes[0]["max_tokens"] == 700


def test_json_invalide_une_fois_nouvel_essai_reussi(fabriquer) -> None:
    workflow, fm = fabriquer("json_invalide_une_fois")
    resultat = workflow.traiter(_note(NOTE_XSS))

    assert len(fm.requetes) == 2
    assert isinstance(resultat, Fiche) and resultat.statut == Statut.OK
    assert resultat.titre.startswith("[adapté] ")


def test_json_invalide_repli_apres_un_seul_nouvel_essai(fabriquer, constats) -> None:
    workflow, fm = fabriquer("json_invalide")
    resultat = workflow.traiter(_note(NOTE_XSS))

    assert len(fm.requetes) == 2
    assert isinstance(resultat, Fiche) and resultat.statut == Statut.A_REVOIR
    assert _codes(resultat) == [CodeMotif.REPLI_SORTIE_INVALIDE]
    constat = next(c for c in constats if c.id == resultat.tracabilite.constat_id)
    assert resultat.titre == constat.titre
    assert resultat.recommandation == constat.recommandation
    assert resultat.cvss == cvss31.evaluer(constat.cvss_vecteur)


def test_erreur_500_repli_moteur_immediat(fabriquer) -> None:
    workflow, fm = fabriquer("erreur_500")
    resultat = workflow.traiter(_note(NOTE_XSS))

    assert len(fm.requetes) == 1
    assert isinstance(resultat, Fiche) and resultat.statut == Statut.A_REVOIR
    assert _codes(resultat) == [CodeMotif.REPLI_MOTEUR]


def test_rubrique_absente_vaut_sortie_invalide(fabriquer, monkeypatch) -> None:
    workflow, _ = fabriquer("nominal")
    appels: list[int] = []

    def generer_incomplet(messages, schema, *, max_tokens):
        appels.append(1)
        return {"titre": "un titre assez long pour passer", "description": 3}

    monkeypatch.setattr(workflow._ports.moteur, "generer_json", generer_incomplet)
    resultat = workflow.traiter(_note(NOTE_XSS))

    assert len(appels) == 2
    assert isinstance(resultat, Fiche)
    assert _codes(resultat) == [CodeMotif.REPLI_SORTIE_INVALIDE]


def test_references_inventees_retirees(fabriquer) -> None:
    workflow, fm = fabriquer("references_inventees")
    resultat = workflow.traiter(_note(NOTE_XSS))

    assert len(fm.requetes) == 1
    assert isinstance(resultat, Fiche) and resultat.statut == Statut.A_REVOIR
    retires = {m.detail for m in resultat.motifs if m.code == CodeMotif.REFERENCE_RETIREE}
    assert retires == {"CWE-9999", "CVE-2099-0001", "https://exemple.invalid/x"}
    for jeton in retires:
        assert jeton not in resultat.description


def test_vecteur_invalide_vecteur_par_defaut_sans_nouvel_essai(fabriquer, constats) -> None:
    workflow, fm = fabriquer("vecteur_invalide")
    resultat = workflow.traiter(_note(NOTE_XSS))

    assert len(fm.requetes) == 1
    assert isinstance(resultat, Fiche)
    assert _codes(resultat) == [CodeMotif.VECTEUR_INVALIDE]
    constat = next(c for c in constats if c.id == resultat.tracabilite.constat_id)
    assert resultat.cvss == cvss31.evaluer(constat.cvss_vecteur)
    assert resultat.titre.startswith("[adapté] ")


def test_note_invalide_non_traitee(fabriquer) -> None:
    workflow, fm = fabriquer("nominal")
    resultat = workflow.traiter(NoteInvalide(fichier="casse.md", raison="YAML illisible"))

    assert isinstance(resultat, EntreeEcartee)
    assert resultat.statut == Statut.NON_TRAITEE
    assert resultat.motif.code == CodeMotif.NOTE_INVALIDE
    assert resultat.motif.detail == "YAML illisible"
    assert fm.requetes == []


def test_note_hors_sujet_non_rattachee_sans_requete(fabriquer) -> None:
    workflow, fm = fabriquer("nominal")
    resultat = workflow.traiter(_note("hors-sujet.md", NOTES_TEST))

    assert isinstance(resultat, EntreeEcartee)
    assert resultat.statut == Statut.NON_RATTACHEE
    assert resultat.motif.code == CodeMotif.AUCUN_CONSTAT
    assert len(resultat.candidats) == 3
    assert fm.requetes == []


def test_troncature_motif_note_tronquee(fabriquer) -> None:
    workflow, fm = fabriquer("nominal", taille_max_note=80)
    note = _note(NOTE_XSS)
    resultat = workflow.traiter(note)

    assert isinstance(resultat, Fiche) and resultat.statut == Statut.A_REVOIR
    assert _codes(resultat) == [CodeMotif.NOTE_TRONQUEE]
    contenu = fm.requetes[0]["messages"][-1]["content"]
    assert note.corps[:80] + prompt.MARQUE_TRONCATURE + "</note>" in contenu
    assert note.corps[:81] not in contenu


def test_troncature_conservee_dans_le_repli(fabriquer) -> None:
    workflow, _ = fabriquer("erreur_500", taille_max_note=80)
    resultat = workflow.traiter(_note(NOTE_XSS))

    assert isinstance(resultat, Fiche)
    assert _codes(resultat) == [CodeMotif.NOTE_TRONQUEE, CodeMotif.REPLI_MOTEUR]


def test_prompt_balises_dans_le_dernier_user_sans_references_ni_attendu(constats) -> None:
    constat = next(c for c in constats if c.id == "WEB-XSS-REFLECHI")
    note = Note(
        fichier="n.md",
        titre="Titre",
        actif="https://portail.exemple.test",
        severite_pressentie=None,
        constat_attendu="ATTENDU-SECRET",
        corps="Le paramètre q est renvoyé sans échappement.",
    )
    messages = prompt.construire(note, constat, "/no_think", 6000)

    assert [m["role"] for m in messages] == ["system", "user"]
    assert messages[0]["content"].startswith("/no_think\n")
    assert "JSON" in messages[0]["content"]
    contenu = messages[-1]["content"]
    debut, fin = contenu.index("<constat>"), contenu.index("</constat>")
    assert debut < fin < contenu.index("<note>") < contenu.index("</note>")
    donnees = json.loads(contenu[debut + len("<constat>") : fin])
    attendus = {"id", "titre", "description", "impact", "recommandation", "cvss_vecteur"}
    assert set(donnees) == attendus
    assert "Actif : https://portail.exemple.test\n" in contenu
    assert "ATTENDU-SECRET" not in contenu
    assert "references" not in contenu
    for reference in constat.references:
        assert reference.url not in contenu
    assert prompt.MARQUE_TRONCATURE not in contenu


def test_prompt_sans_prefixe_ni_actif(constats) -> None:
    note = Note(
        fichier="n.md",
        titre=None,
        actif=None,
        severite_pressentie=None,
        constat_attendu=None,
        corps="corps",
    )
    messages = prompt.construire(note, constats[0], "", 6000)

    assert messages[0]["content"] == prompt.CONSIGNE
    assert "Actif" not in messages[1]["content"]
    assert messages[1]["content"].endswith("<note>corps</note>")


def test_prefixe_systeme_vient_des_ports(fabriquer) -> None:
    workflow, fm = fabriquer("nominal", prefixe="/no_think")
    workflow.traiter(_note(NOTE_XSS))

    assert fm.requetes[0]["messages"][0]["content"].startswith("/no_think\n")


def test_preparer_et_assembler(fabriquer) -> None:
    workflow, _ = fabriquer("nominal")
    invalide = NoteInvalide(fichier="casse.md", raison="x")
    workflow._ports.source_notes.elements = [_note(NOTE_XSS), invalide]

    elements = workflow.preparer(Path("dossier"))
    assert workflow._ports.source_notes.lus == [Path("dossier")]
    resultats = [workflow.traiter(e) for e in elements]
    rapport = workflow.assembler(resultats)

    assert [f.tracabilite.note for f in rapport.fiches] == [NOTE_XSS]
    assert [e.note for e in rapport.ecartees] == ["casse.md"]
