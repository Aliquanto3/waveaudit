"""Écrivain unique de `journal.jsonl` (`application/journal.JournalLot`, C1)."""

from datetime import datetime

from waveaudit.application.journal import JournalLot
from waveaudit.domaine.modeles import EvenementLot, Statut, TypeEvenement


def _evenement(type_: TypeEvenement, **champs) -> EvenementLot:
    donnees = {
        "type": type_,
        "horodatage": datetime.now().astimezone(),
        "index": None,
        "total": 2,
        "note": None,
        "statut": None,
        "duree_s": None,
    }
    return EvenementLot(**(donnees | champs))


def test_une_ligne_par_evenement_videe_aussitot(tmp_path):
    chemin = tmp_path / "journal.jsonl"
    demarre = _evenement(TypeEvenement.LOT_DEMARRE, details={"workflow": "incident"})
    termine = _evenement(
        TypeEvenement.FICHE_TERMINEE, index=1, note="INC-WIN-FORCE-BRUTE", statut=Statut.OK
    )
    with JournalLot(chemin) as journal:
        journal.ecrire(demarre)
        # flush après chaque événement : lisible avant la fermeture
        assert chemin.read_text(encoding="utf-8").splitlines() == [demarre.model_dump_json()]
        journal.ecrire(termine)
    lignes = chemin.read_text(encoding="utf-8").splitlines()
    assert [EvenementLot.model_validate_json(ligne) for ligne in lignes] == [demarre, termine]


def test_ajout_sans_ecraser(tmp_path):
    chemin = tmp_path / "journal.jsonl"
    premier = _evenement(TypeEvenement.LOT_DEMARRE)
    second = _evenement(TypeEvenement.LOT_ECHOUE, details={"erreur": "MoteurInjoignable"})
    with JournalLot(chemin) as journal:
        journal.ecrire(premier)
    with JournalLot(chemin) as journal:
        journal.ecrire(second)
    assert chemin.read_text(encoding="utf-8").splitlines() == [
        premier.model_dump_json(),
        second.model_dump_json(),
    ]
