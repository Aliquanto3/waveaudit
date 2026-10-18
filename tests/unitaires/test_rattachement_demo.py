"""Calibrage du rattachement BM25 sur les notes de démonstration (CAP-5, Q4).

Charge le vrai catalogue (`donnees/catalogue`, index bilingue) et les vraies notes
(`donnees/demo/notes`), classe chaque note et vérifie les seuils de CAP-5.

Notes 01 et 29 : chacune doit être rattachée au rang 1 (bloquant, Q4).
Notes 01-20 : top1 >= 17/20 et top3 = 20/20 (bloquant).
Notes non vues 21-28 et 30 (la note 29, cible du réglage, n'en fait plus partie) :
top1 >= 8/9 et top3 = 9/9. Valeurs figées en fin de story (commit Q4) : non bloquant
pendant le réglage (xfail retiré), puisque le seuil est déjà atteint sans réglage
supplémentaire — voir le message du commit Q4 pour les essais tentés.
"""

from waveaudit.adaptateurs.catalogue_yaml import CatalogueYaml
from waveaudit.adaptateurs.notes_fichiers import NotesFichiers
from waveaudit.application.config import racine_projet
from waveaudit.domaine.configuration import ConfigRecherche
from waveaudit.domaine.modeles import Note
from waveaudit.domaine.recherche import classer, requete_depuis_note

SEUIL_TOP3 = 20
SEUIL_TOP1 = 17
SEUIL_TOP3_NON_VUES = 9  # sur 9 notes (21-28, 30)
SEUIL_TOP1_NON_VUES = 8


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


def test_rattachement_atteint_le_seuil_cap5():
    """Notes 01-20 : top1 >= 17/20, top3 = 20/20 (Q4)."""
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


def test_note_01_rattachee_au_rang_1():
    """Note 01 (XSS réfléchi) : rattachement exact au rang 1 (Q4)."""
    rangs = _rangs_des_notes()
    rang = next(r for f, r in rangs.items() if f.startswith("01-"))
    assert rang == 1, f"rang={rang}"


def test_note_29_rattachee_au_rang_1():
    """Note 29 (SSTI) : rattachement exact au rang 1 (Q4)."""
    rangs = _rangs_des_notes()
    rang = next(r for f, r in rangs.items() if f.startswith("29-"))
    assert rang == 1, f"rang={rang}"


def test_rattachement_des_notes_non_vues():
    """Notes non vues 21-28 et 30 (la 29 en est sortie) : top1 >= 8/9, top3 = 9/9 (Q4)."""
    rangs = {
        f: r for f, r in _rangs_des_notes().items() if 21 <= _prefixe(f) <= 28 or _prefixe(f) == 30
    }
    assert len(rangs) == 9

    top1 = sum(1 for rang in rangs.values() if rang == 1)
    top3 = sum(1 for rang in rangs.values() if rang is not None and rang <= 3)

    matrice = "\n".join(f"  {fichier}: rang={rang}" for fichier, rang in sorted(rangs.items()))
    assert top3 >= SEUIL_TOP3_NON_VUES, f"top3={top3}/9 (seuil {SEUIL_TOP3_NON_VUES}) :\n{matrice}"
    assert top1 >= SEUIL_TOP1_NON_VUES, f"top1={top1}/9 (seuil {SEUIL_TOP1_NON_VUES}) :\n{matrice}"
