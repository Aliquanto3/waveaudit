"""Noms publics de `application/lot.py` (contrats §9 v2, CAP-16, revue A3)."""

import pytest

from waveaudit.application import lot
from waveaudit.domaine.erreurs import EntreeInvalide


@pytest.fixture
def config(config_test):
    return config_test


def test_dossier_sorties(config):
    assert lot.dossier_sorties(config) == config.chemins.var / "sorties"


@pytest.mark.parametrize("id_lot", ["a", "20261018-120000", "x" * 64, "A-b-9"])
def test_motif_id_lot_admis(id_lot):
    assert lot.MOTIF_ID_LOT.fullmatch(id_lot)


@pytest.mark.parametrize("id_lot", ["", "x" * 65, "-tiret", "a b", "../evasion", "a.b", "é"])
def test_motif_id_lot_refuse(id_lot):
    assert not lot.MOTIF_ID_LOT.fullmatch(id_lot)


def test_dossier_lot_existant_ne_cree_rien(config):
    sorties = lot.dossier_sorties(config)
    assert lot.dossier_lot_existant("20261018-120000", config) is None
    assert not sorties.exists()
    (sorties / "20261018-120000").mkdir(parents=True)
    assert lot.dossier_lot_existant("20261018-120000", config) == sorties / "20261018-120000"
    assert lot.dossier_lot_existant("20261018-120001", config) is None
    assert sorted(p.name for p in sorties.iterdir()) == ["20261018-120000"]


def test_dossier_lot_existant_fichier_et_motif(config):
    sorties = lot.dossier_sorties(config)
    sorties.mkdir(parents=True)
    (sorties / "fichier").write_text("x", encoding="utf-8")
    assert lot.dossier_lot_existant("fichier", config) is None
    assert lot.dossier_lot_existant("x" * 65, config) is None
    assert lot.dossier_lot_existant("..", config) is None


@pytest.mark.parametrize("id_lot", ["NUL", "nul", "CON", "com1", "LPT9", "aux", "PRN"])
def test_dossier_lot_existant_nom_reserve(config, id_lot):
    assert lot.dossier_lot_existant(id_lot, config) is None
    assert not lot.dossier_sorties(config).exists()


def test_verifier_id_lot_cree_le_dossier(config):
    dossier = lot.verifier_id_lot("lot-1", config)
    assert dossier == lot.dossier_sorties(config) / "lot-1"
    assert dossier.is_dir()
    assert lot.verifier_id_lot("lot-1", config) == dossier  # dossier existant admis


@pytest.mark.parametrize("id_lot", ["x" * 65, "NUL", "con", "-tiret", "a b", "../evasion"])
def test_verifier_id_lot_refuse(config, id_lot):
    with pytest.raises(EntreeInvalide):
        lot.verifier_id_lot(id_lot, config)


def test_sans_chemin_public():
    assert lot.sans_chemin(r"C:\Users\x\notes\a.md absent") == "a.md absent"


def test_emetteur_public(tmp_path):
    from waveaudit.application.journal import JournalLot
    from waveaudit.domaine.modeles import TypeEvenement

    recus = []
    with JournalLot(tmp_path / "journal.jsonl") as journal:
        emetteur = lot.Emetteur(journal, recus.append)
        emetteur.total = 2
        emetteur.emettre(TypeEvenement.LOT_DEMARRE, details={"id_lot": "x"})
    assert [e.type for e in recus] == [TypeEvenement.LOT_DEMARRE]
    assert recus[0].total == 2
    assert (tmp_path / "journal.jsonl").read_text(encoding="utf-8").count("\n") == 1
