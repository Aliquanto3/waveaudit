"""Bout en bout sur le vrai moteur (marqueur `slow`, sauté si `var/modeles` ou `llama-server`
sont absents : lancer `waveaudit installer`). Mode `local-gere` de la configuration livrée, 2
notes de démonstration. Assertions de structure seulement : la qualité réelle (0 référence
inventée, ≥ 70 % utilisables) se juge hors nuit, avec `slm-quality-bench` (SPEC §Assumptions).

Écrit transitoirement dans `var/sorties/<id_lot>` et `var/journaux/` du dépôt, le temps du test
(il réutilise les artefacts déjà installés là), puis nettoie ces deux chemins dans tous les cas.
"""

import shutil

import pytest
from docx import Document

from waveaudit.application.config import charger_configuration, racine_projet
from waveaudit.application.lot import executer_lot
from waveaudit.domaine.modeles import RequeteLot
from waveaudit.installation import manifeste

pytestmark = pytest.mark.slow

DEMO = racine_projet() / "donnees" / "demo" / "notes"
ID_LOT = "test-reel-e2e"


def test_lot_reel_deux_notes_mode_local_gere(tmp_path):
    config = charger_configuration()
    var = config.chemins.var
    artefacts = manifeste.charger(config.chemins.manifeste)
    binaire = manifeste.chemin(manifeste.par_role(artefacts, "moteur"), var)
    gguf = manifeste.chemin(manifeste.par_role(artefacts, "modele_defaut"), var)
    if not (var / "modeles").is_dir() or not binaire.is_file() or not gguf.is_file():
        pytest.skip("var/modeles ou llama-server absent : lancer `waveaudit installer`")
    if config.moteur.mode != "local-gere":
        pytest.skip("configuration locale surchargée en mode externe (waveaudit.local.toml)")

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
            assert (fiche.statut == "a_revoir") == bool(fiche.motifs)
        Document(str(resultat.chemin_rapport))  # lève si le .docx est invalide
    finally:
        shutil.rmtree(dossier_sortie, ignore_errors=True)
        journal_moteur.unlink(missing_ok=True)
