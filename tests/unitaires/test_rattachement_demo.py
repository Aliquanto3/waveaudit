"""Calibrage du rattachement BM25 sur les 20 notes de démonstration (CAP-3, story 11).

Charge le vrai catalogue (`donnees/catalogue`) et les vraies notes
(`donnees/demo/notes`), classe chaque note et vérifie le seuil de CAP-3 :
au moins 18 notes dans le top 3 et 15 en premier, sans appel au modèle.
"""

from waveaudit.adaptateurs.catalogue_yaml import CatalogueYaml
from waveaudit.adaptateurs.notes_fichiers import NotesFichiers
from waveaudit.application.config import racine_projet
from waveaudit.domaine.configuration import ConfigRecherche
from waveaudit.domaine.modeles import Note
from waveaudit.domaine.recherche import classer, requete_depuis_note

SEUIL_TOP3 = 18
SEUIL_TOP1 = 15


def _rang(note: Note, constats, reglages: ConfigRecherche) -> int | None:
    candidats = classer(constats, requete_depuis_note(note), k1=reglages.k1, b=reglages.b)
    ids = [c.id for c in candidats]
    try:
        return ids.index(note.constat_attendu) + 1
    except ValueError:
        return None


def test_rattachement_atteint_le_seuil_cap3():
    constats = CatalogueYaml(racine_projet() / "donnees" / "catalogue").constats()
    reglages = ConfigRecherche()
    notes = NotesFichiers().lire(racine_projet() / "donnees" / "demo" / "notes")

    rangs: dict[str, int | None] = {}
    for note in notes:
        assert isinstance(note, Note), note
        assert note.constat_attendu is not None, note.fichier
        rangs[note.fichier] = _rang(note, constats, reglages)

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
