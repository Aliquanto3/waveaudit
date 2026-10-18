"""Fiche d'un lot et liste des lots, lues sur le disque (contrats §30, CAP-9, CAP-10)."""

import json
from datetime import datetime, timedelta

from waveaudit.application import composition
from waveaudit.application import lots as lots_app
from waveaudit.application.lot import dossier_sorties
from waveaudit.application.moteur_demande import Occupation

_ISO = "2026-10-18T09:14:00+02:00"


def _dossier(config, id_lot: str):
    dossier = dossier_sorties(config) / id_lot
    dossier.mkdir(parents=True, exist_ok=True)
    return dossier


def _ecrire_lot_json(dossier, **champs) -> None:
    base = {
        "id_lot": dossier.name,
        "workflow": "fiches",
        "langue": "fr",
        "modele_demande": None,
        "cree_le": _ISO,
        "pid": 999999,
    }
    (dossier / "lot.json").write_text(
        json.dumps(base | champs, ensure_ascii=False), encoding="utf-8"
    )


def _ecrire_journal(dossier, *lignes: dict | str) -> None:
    texte = "\n".join(ligne if isinstance(ligne, str) else json.dumps(ligne) for ligne in lignes)
    (dossier / "journal.jsonl").write_text(texte + "\n", encoding="utf-8")


def _demarre(total: int = 2, modele: str = "granite") -> dict:
    return {
        "type": "lot_demarre",
        "horodatage": _ISO,
        "index": None,
        "total": total,
        "note": None,
        "statut": None,
        "duree_s": None,
        "details": {"modele": modele},
    }


def _termine() -> dict:
    return {
        "type": "lot_termine",
        "horodatage": _ISO,
        "index": None,
        "total": 2,
        "note": None,
        "statut": None,
        "duree_s": 1.0,
        "details": {},
    }


def _echoue(message: str = "boum") -> dict:
    return {
        "type": "lot_echoue",
        "horodatage": _ISO,
        "index": None,
        "total": 2,
        "note": None,
        "statut": None,
        "duree_s": None,
        "details": {"erreur": "ValueError", "message": message},
    }


def test_workflow_et_url_depuis_lot_json(config_test):
    dossier = _dossier(config_test, "incident-1")
    _ecrire_lot_json(dossier, workflow="incident")
    _ecrire_journal(dossier, _demarre(), _termine())

    etat = lots_app.etat_lot(config_test, "incident-1", None)
    assert etat["workflow"] == "incident"

    resume = lots_app.lister_lots(config_test, None)[0]
    assert resume.workflow == "incident"
    assert resume.url == "/incidents/incident-1"


def test_etat_termine_et_echoue(config_test):
    termine = _dossier(config_test, "lot-termine")
    _ecrire_lot_json(termine)
    _ecrire_journal(termine, _demarre(), _termine())

    echoue = _dossier(config_test, "lot-echoue")
    _ecrire_lot_json(echoue)
    _ecrire_journal(echoue, _demarre(), _echoue("le moteur ne répond pas"))

    assert lots_app.etat_lot(config_test, "lot-termine", None)["etat"] == "termine"
    etat_echoue = lots_app.etat_lot(config_test, "lot-echoue", None)
    assert etat_echoue["etat"] == "echoue"
    assert etat_echoue["erreur"] == "le moteur ne répond pas"
    assert etat_echoue["total"] == 2


def test_en_cours_par_occupation_de_ce_processus(config_test, monkeypatch):
    dossier = _dossier(config_test, "lot-en-cours")
    _ecrire_lot_json(dossier, pid=999999)
    _ecrire_journal(dossier, _demarre())
    monkeypatch.setattr(composition, "processus_actif", lambda pid, cree_le: False)

    occupation = Occupation("fiches", "lot-en-cours", None, datetime.now().astimezone())
    etat = lots_app.etat_lot(config_test, "lot-en-cours", occupation)
    assert etat["etat"] == "en_cours"

    # Une autre occupation (autre lot, ou régénération) ne rend pas ce lot en_cours.
    autre = Occupation("fiches", "un-autre-lot", None, datetime.now().astimezone())
    etat_sans = lots_app.etat_lot(config_test, "lot-en-cours", autre)
    assert etat_sans["etat"] == "interrompu"


def test_lot_v010_sans_lot_json(config_test):
    """Un lot v0.1.0 (sans `lot.json`) reste lisible via le seul journal (§30)."""
    dossier = _dossier(config_test, "v010")
    _ecrire_journal(dossier, _demarre(), _termine())

    etat = lots_app.etat_lot(config_test, "v010", None)
    assert etat["workflow"] == "fiches"
    assert etat["etat"] == "termine"


def test_ligne_illisible_ignoree(config_test):
    dossier = _dossier(config_test, "ligne-illisible")
    _ecrire_lot_json(dossier)
    _ecrire_journal(dossier, _demarre(), "{ceci n'est pas du json", _termine())

    etat = lots_app.etat_lot(config_test, "ligne-illisible", None)
    assert [e["type"] for e in etat["evenements"]] == ["lot_demarre", "lot_termine"]


def test_pid_vivant_autre_processus_en_cours_externe(config_test, monkeypatch):
    dossier = _dossier(config_test, "pid-vivant")
    _ecrire_lot_json(dossier, pid=4242)
    _ecrire_journal(dossier, _demarre())
    monkeypatch.setattr(composition, "processus_actif", lambda pid, cree_le: True)

    etat = lots_app.etat_lot(config_test, "pid-vivant", None)
    assert etat["etat"] == "en_cours"

    resume = lots_app.lister_lots(config_test, None)[0]
    assert resume.externe is True


def test_pid_mort_interrompu(config_test, monkeypatch):
    dossier = _dossier(config_test, "pid-mort")
    _ecrire_lot_json(dossier, pid=4242)
    _ecrire_journal(dossier, _demarre())
    monkeypatch.setattr(composition, "processus_actif", lambda pid, cree_le: False)

    assert lots_app.etat_lot(config_test, "pid-mort", None)["etat"] == "interrompu"


def test_tri_par_cree_le_decroissant(config_test):
    ancien = _dossier(config_test, "ancien")
    _ecrire_lot_json(ancien, cree_le=(datetime.now().astimezone() - timedelta(hours=1)).isoformat())
    _ecrire_journal(ancien, _demarre(), _termine())

    recent = _dossier(config_test, "recent")
    _ecrire_lot_json(recent, cree_le=datetime.now().astimezone().isoformat())
    _ecrire_journal(recent, _demarre(), _termine())

    resumes = lots_app.lister_lots(config_test, None)
    assert [r.id_lot for r in resumes] == ["recent", "ancien"]
