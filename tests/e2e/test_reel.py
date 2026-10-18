"""Bout en bout sur le vrai moteur (marqueur `slow`, sauté si `var/modeles` ou `llama-server`
sont absents : lancer `waveaudit installer`). Mode `local-gere` de la configuration livrée, 2
notes de démonstration. Assertions de structure seulement : la qualité réelle (0 référence
inventée, ≥ 70 % utilisables) se juge hors nuit, avec `slm-quality-bench` (SPEC §Assumptions).

Écrit transitoirement dans `var/sorties/<id_lot>` et `var/journaux/` du dépôt, le temps du test
(il réutilise les artefacts déjà installés là), puis nettoie ces deux chemins dans tous les cas.
"""

import json
import shutil

import pytest
from docx import Document

from waveaudit.adaptateurs.export_docx import BANDEAU
from waveaudit.adaptateurs.moteur_openai import MoteurOpenAI
from waveaudit.application.banc import executer_banc
from waveaudit.application.config import charger_configuration, racine_projet
from waveaudit.application.lot import executer_lot
from waveaudit.domaine.modeles import CodeMotif, RequeteLot, Statut
from waveaudit.installation import manifeste

pytestmark = pytest.mark.slow

DEMO = racine_projet() / "donnees" / "demo" / "notes"
ID_LOT = "test-reel-e2e"
ID_LOT_PENALITE = "test-reel-e2e-penalite"
NOTES_BANC = ("01-xss-reflechi.md", "11-kerberoasting.md")
# [revue V1] Plafond contre un retour vers la recopie du prompt livré (0,93) : ce n'est pas le
# seuil de CAP-6 (médiane < 0,7 sur 3 seeds), mesuré par le rebanc (mesures-qualite.md).
PLAFOND_RECOPIE = 0.8


def _config_reelle():
    """Configuration livrée, ou `skip` si le moteur ou le modèle par défaut manque."""
    config = charger_configuration()
    var = config.chemins.var
    artefacts = manifeste.charger(config.chemins.manifeste)
    binaire = manifeste.chemin(manifeste.par_role(artefacts, "moteur"), var)
    gguf = manifeste.chemin(manifeste.par_role(artefacts, "modele_defaut"), var)
    if not (var / "modeles").is_dir() or not binaire.is_file() or not gguf.is_file():
        pytest.skip("var/modeles ou llama-server absent : lancer `waveaudit installer`")
    if config.moteur.mode != "local-gere":
        pytest.skip("configuration locale surchargée en mode externe (waveaudit.local.toml)")
    return config, artefacts


def _notes_banc(tmp_path):
    notes = tmp_path / "notes"
    notes.mkdir()
    for nom in NOTES_BANC:
        shutil.copy(DEMO / nom, notes)
    return notes


def test_lot_reel_deux_notes_mode_local_gere(tmp_path):
    config, _ = _config_reelle()
    var = config.chemins.var

    notes = tmp_path / "notes"
    notes.mkdir()
    for chemin in sorted(DEMO.iterdir())[:2]:
        shutil.copy(chemin, notes)

    dossier_sortie = var / "sorties" / ID_LOT
    journal_moteur = var / "journaux" / f"llama-server-{ID_LOT}.log"
    try:
        resultat = executer_lot(RequeteLot(dossier=notes, id_lot=ID_LOT), config)

        assert resultat.id_lot == ID_LOT
        assert resultat.dossier_sortie == dossier_sortie
        assert len(resultat.rapport.fiches) + len(resultat.rapport.ecartees) == 2
        for fiche in resultat.rapport.fiches:
            assert fiche.titre and fiche.description and fiche.impact and fiche.recommandation
        document = Document(str(resultat.chemin_rapport))  # lève si le .docx est invalide
        for section in document.sections:
            assert BANDEAU in [p.text for p in section.header.paragraphs]
    finally:
        shutil.rmtree(dossier_sortie, ignore_errors=True)
        journal_moteur.unlink(missing_ok=True)


def test_lot_reel_deux_notes_repeat_penalty_du_manifeste(tmp_path, monkeypatch):
    """Q5 (CAP-6) : le vrai moteur reçoit le `repeat_penalty` du manifeste ; fiches `ok`, fr."""
    config, artefacts = _config_reelle()
    var = config.chemins.var
    attendu = manifeste.par_role(artefacts, "modele_defaut").repeat_penalty
    assert attendu is not None  # mesuré au rebanc (bilan-modeles.md, section v2)
    vus: list[float] = []
    original = MoteurOpenAI.generer_json

    def espion(self, *args, **kwargs):
        vus.append(self._repeat_penalty)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(MoteurOpenAI, "generer_json", espion)
    dossier_sortie = var / "sorties" / ID_LOT_PENALITE
    journal_moteur = var / "journaux" / f"llama-server-{ID_LOT_PENALITE}.log"
    try:
        requete = RequeteLot(dossier=_notes_banc(tmp_path), id_lot=ID_LOT_PENALITE, langue="fr")
        resultat = executer_lot(requete, config)

        assert vus and set(vus) == {attendu}
        assert len(resultat.rapport.fiches) == 2 and not resultat.rapport.ecartees
        for fiche in resultat.rapport.fiches:
            codes = [motif.code for motif in fiche.motifs]
            assert fiche.statut == Statut.OK, (fiche.note, codes)
            assert CodeMotif.LANGUE not in codes and CodeMotif.REPETITION not in codes
    finally:
        shutil.rmtree(dossier_sortie, ignore_errors=True)
        journal_moteur.unlink(missing_ok=True)


def test_banc_reel_deux_notes_plafond_recopie(tmp_path):
    """[revue V1] Banc réel sur 01 et 11, modèle par défaut : recopie <= `PLAFOND_RECOPIE`."""
    config, _ = _config_reelle()
    var = config.chemins.var
    chemin = executer_banc(_notes_banc(tmp_path), config)
    try:
        banc = json.loads(chemin.read_text(encoding="utf-8"))

        assert banc["ok"] + banc["a_revoir"] == 2
        assert banc["recopie"] is not None, "aucune fiche mesurable (2 replis)"
        assert banc["recopie"] <= PLAFOND_RECOPIE, banc["recopie_par_rubrique"]
    finally:
        # Seul le lot de ce banc est retiré : `var/sorties` peut contenir d'autres lots.
        (var / "journaux" / f"llama-server-{chemin.parent.name}.log").unlink(missing_ok=True)
        shutil.rmtree(chemin.parent, ignore_errors=True)
