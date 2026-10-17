"""Service de lot de bout en bout (contrats §9, AD-2, AD-8), faux moteur en mode externe."""

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

import pytest
from docx import Document

from waveaudit.application import lot
from waveaudit.application.config import racine_projet
from waveaudit.application.lot import executer_lot, nouvel_id_lot
from waveaudit.domaine.erreurs import EntreeInvalide, MoteurInjoignable
from waveaudit.domaine.modeles import Rapport, RequeteLot, TypeEvenement

DEMO = racine_projet() / "donnees" / "demo" / "notes"
T = TypeEvenement


def _vers(config, fm):
    return config.model_copy(
        update={"moteur": config.moteur.model_copy(update={"base_url": fm.base_url})}
    )


def _journal(resultat_ou_dossier) -> list[dict]:
    dossier = getattr(resultat_ou_dossier, "dossier_sortie", resultat_ou_dossier)
    texte = (Path(dossier) / "journal.jsonl").read_text(encoding="utf-8")
    return [json.loads(ligne) for ligne in texte.splitlines()]


def test_lot_nominal_30_notes(config_test, tmp_path):
    recus = []
    copie = tmp_path / "copie.docx"
    resultat = executer_lot(
        RequeteLot(dossier=DEMO, copie_rapport=copie), config_test, recus.append
    )

    sortie = resultat.dossier_sortie
    assert sortie == config_test.chemins.var / "sorties" / resultat.id_lot
    rapport = Rapport.model_validate_json((sortie / "fiches.json").read_text(encoding="utf-8"))
    assert rapport == resultat.rapport
    assert len(rapport.fiches) + len(rapport.ecartees) == 30
    assert resultat.chemin_rapport == sortie / "rapport.docx"
    Document(str(resultat.chemin_rapport))
    assert copie.read_bytes() == resultat.chemin_rapport.read_bytes()

    evenements = _journal(resultat)
    assert [e["type"] for e in evenements] == [e.type for e in recus]
    types = [e["type"] for e in evenements]
    assert types[0] == T.LOT_DEMARRE and types[-1] == T.LOT_TERMINE
    demarre = evenements[0]
    assert demarre["total"] == 30
    assert demarre["details"] == {
        "id_lot": resultat.id_lot,
        "modele": "externe",
        "pid_moteur": None,
    }
    fiches = evenements[1:-1]
    assert len(fiches) == 60
    for i in range(30):
        debut, fin = fiches[2 * i], fiches[2 * i + 1]
        assert debut["type"] == T.FICHE_DEMARREE and debut["index"] == i + 1
        assert fin["index"] == i + 1 and fin["note"] == debut["note"]
        assert fin["type"] in (T.FICHE_TERMINEE, T.FICHE_NON_TRAITEE, T.FICHE_NON_RATTACHEE)
        assert fin["duree_s"] >= 0
        assert "/" not in fin["note"] and "\\" not in fin["note"]
    notes = [e["note"] for e in fiches[::2]]
    assert notes == sorted(notes, key=str.casefold)
    assert str(tmp_path) not in (sortie / "journal.jsonl").read_text(encoding="utf-8")


def test_id_lot_unique_dans_la_meme_seconde(config_test, monkeypatch):
    fige = datetime(2026, 10, 17, 12, 0, 0).astimezone()
    monkeypatch.setattr(lot, "_maintenant", lambda: fige)
    var = config_test.chemins.var
    assert nouvel_id_lot(var) == "20261017-120000"
    assert nouvel_id_lot(var) == "20261017-120000-2"
    a = executer_lot(RequeteLot(dossier=DEMO), config_test)
    b = executer_lot(RequeteLot(dossier=DEMO), config_test)
    assert (a.id_lot, b.id_lot) == ("20261017-120000-3", "20261017-120000-4")


def test_sonde_ko_lot_echoue_puis_moteur_injoignable(config_test, faux_moteur):
    config = _vers(config_test, faux_moteur("injoignable"))
    recus = []
    with pytest.raises(MoteurInjoignable):
        executer_lot(RequeteLot(dossier=DEMO, id_lot="lot-ko"), config, recus.append)
    evenements = _journal(config.chemins.var / "sorties" / "lot-ko")
    assert [e["type"] for e in evenements] == [T.LOT_ECHOUE]
    assert evenements[0]["details"]["erreur"] == "MoteurInjoignable"
    assert [e.type for e in recus] == [T.LOT_ECHOUE]


def test_abonne_qui_leve_n_arrete_pas_le_lot(config_test):
    def abonne(evenement):
        raise RuntimeError("abonné cassé")

    resultat = executer_lot(RequeteLot(dossier=DEMO), config_test, abonne)
    assert _journal(resultat)[-1]["type"] == T.LOT_TERMINE


def test_entrees_invalides(config_test, tmp_path):
    with pytest.raises(EntreeInvalide):
        executer_lot(RequeteLot(dossier=tmp_path / "absent"), config_test)
    with pytest.raises(EntreeInvalide):
        executer_lot(RequeteLot(dossier=DEMO, workflow="inconnu"), config_test)
    with pytest.raises(EntreeInvalide):
        executer_lot(RequeteLot(dossier=DEMO, id_lot="../evasion"), config_test)
    if sys.platform == "win32":  # nom réservé : mkdir ne crée rien
        with pytest.raises(EntreeInvalide):
            executer_lot(RequeteLot(dossier=DEMO, id_lot="NUL"), config_test)


@pytest.mark.parametrize(
    "message",
    [
        r"C:\Users\Prénom Nom\proj\var\llama-server.exe absent : lancer l'installation",
        str(FileNotFoundError(2, "introuvable", r"C:\Users\Prénom Nom\notes\x.md")),
        "voir /home/Prénom Nom/var/journaux/l.log",
    ],
)
def test_sans_chemin_avec_espaces(message):
    nettoye = lot._sans_chemin(message)
    assert "Prénom" not in nettoye and "Users" not in nettoye and "home" not in nettoye


def test_sans_chemin_garde_les_url():
    assert lot._sans_chemin("moteur http://127.0.0.1:8080/v1") == "moteur http://127.0.0.1:8080/v1"


def test_lot_echoue_sans_chemin_absolu(config_test, tmp_path):
    vide = tmp_path / "vide"
    vide.mkdir()
    with pytest.raises(EntreeInvalide):
        executer_lot(RequeteLot(dossier=vide, id_lot="lot-vide"), config_test)
    evenement = _journal(config_test.chemins.var / "sorties" / "lot-vide")[-1]
    assert evenement["type"] == T.LOT_ECHOUE
    assert str(tmp_path) not in evenement["details"]["message"]
    assert "vide" in evenement["details"]["message"]


def test_cap9_deux_moteurs_chacun_son_lot(config_test, faux_moteur, tmp_path):
    lot_a, lot_b = tmp_path / "a", tmp_path / "b"
    lot_a.mkdir()
    lot_b.mkdir()
    notes = sorted(DEMO.iterdir())
    for note in notes[:3]:
        shutil.copy(note, lot_a)
    for note in notes[3:8]:
        shutil.copy(note, lot_b)
    fm_a, fm_b = faux_moteur(), faux_moteur()
    ra = executer_lot(RequeteLot(dossier=lot_a), _vers(config_test, fm_a))
    rb = executer_lot(RequeteLot(dossier=lot_b, modele="modele-b"), _vers(config_test, fm_b))
    # Scénario nominal : un seul appel par fiche rédigée, et chaque appel au moteur de son lot.
    assert ra.rapport.fiches and rb.rapport.fiches
    assert len(fm_a.requetes) == len(ra.rapport.fiches)
    assert len(fm_b.requetes) == len(rb.rapport.fiches)
    assert {r["model"] for r in fm_a.requetes} == {""}
    assert {r["model"] for r in fm_b.requetes} == {"modele-b"}
