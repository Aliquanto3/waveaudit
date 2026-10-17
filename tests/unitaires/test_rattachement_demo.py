"""Calibrage du rattachement BM25 sur les notes de démonstration (CAP-3, story 11, D1).

Charge le vrai catalogue (`donnees/catalogue`) et les vraies notes
(`donnees/demo/notes`), classe chaque note et vérifie le seuil de CAP-3.

Notes 01-20 : seuil inchangé (story 11), bloquant.
Notes 21-30 (difficiles, story D1) : mesure informative top1/top3, non bloquante
(`xfail(strict=False)` si le score est sous 7/10 en top 3).
"""

import pytest

from waveaudit.adaptateurs.catalogue_yaml import CatalogueYaml
from waveaudit.adaptateurs.notes_fichiers import NotesFichiers
from waveaudit.application.config import racine_projet
from waveaudit.domaine.configuration import ConfigRecherche
from waveaudit.domaine.modeles import Note
from waveaudit.domaine.recherche import classer, requete_depuis_note

SEUIL_TOP3 = 18
SEUIL_TOP1 = 15
SEUIL_TOP3_DIFFICILES = 7  # sur 10 notes 21-30 (non bloquant)


def _rang(note: Note, constats, reglages: ConfigRecherche) -> int | None:
    candidats = classer(constats, requete_depuis_note(note), k1=reglages.k1, b=reglages.b)
    ids = [c.id for c in candidats]
    try:
        return ids.index(note.constat_attendu) + 1
    except ValueError:
        return None


def _rangs_des_notes() -> dict[str, int | None]:
    constats = CatalogueYaml(racine_projet() / "donnees" / "catalogue").constats()
    reglages = ConfigRecherche()
    notes = NotesFichiers().lire(racine_projet() / "donnees" / "demo" / "notes")

    rangs: dict[str, int | None] = {}
    for note in notes:
        assert isinstance(note, Note), note
        assert note.constat_attendu is not None, note.fichier
        rangs[note.fichier] = _rang(note, constats, reglages)
    return rangs


def _prefixe(fichier: str) -> int:
    return int(fichier.split("-", 1)[0])


def test_rattachement_atteint_le_seuil_cap3():
    """Notes 01-20 : seuil inchangé depuis la story 11."""
    rangs = {f: r for f, r in _rangs_des_notes().items() if _prefixe(f) <= 20}

    top1 = sum(1 for rang in rangs.values() if rang == 1)
    top3 = sum(1 for rang in rangs.values() if rang is not None and rang <= 3)

    echecs = {fichier: rang for fichier, rang in sorted(rangs.items()) if rang is None or rang > 3}
    matrice = "\n".join(f"  {fichier}: rang={rang}" for fichier, rang in echecs.items())

    assert top3 >= SEUIL_TOP3, (
        f"top3={top3}/{len(rangs)} (seuil {SEUIL_TOP3}) — échecs hors top3 :\n{matrice}"
    )
    assert top1 >= SEUIL_TOP1, (
        f"top1={top1}/{len(rangs)} (seuil {SEUIL_TOP1}) — rangs :\n"
        + "\n".join(f"  {fichier}: rang={rang}" for fichier, rang in sorted(rangs.items()))
    )


def test_rattachement_des_notes_difficiles_21_30():
    """Notes 21-30 (difficiles, D1) : mesure informative top1/top3, non bloquante."""
    rangs = {f: r for f, r in _rangs_des_notes().items() if 21 <= _prefixe(f) <= 30}
    assert len(rangs) == 10

    top1 = sum(1 for rang in rangs.values() if rang == 1)
    top3 = sum(1 for rang in rangs.values() if rang is not None and rang <= 3)

    print(f"\nnotes difficiles 21-30 : top1={top1}/10, top3={top3}/10")
    for fichier, rang in sorted(rangs.items()):
        print(f"  {fichier}: rang={rang}")

    if top3 < SEUIL_TOP3_DIFFICILES:
        pytest.xfail(
            f"top3={top3}/10 (seuil informatif {SEUIL_TOP3_DIFFICILES}) sur les notes difficiles"
        )
