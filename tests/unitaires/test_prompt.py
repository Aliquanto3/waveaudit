"""Échappement des balises `note`/`constat` dans le prompt des fiches (contrats §8, CAP-2)."""

from pathlib import Path

from waveaudit.adaptateurs.catalogue_yaml import CatalogueYaml
from waveaudit.domaine.modeles import ConstatType, Note
from waveaudit.workflows.fiches import prompt

RACINE = Path(__file__).resolve().parents[2]


def _constat() -> ConstatType:
    return CatalogueYaml(RACINE / "donnees" / "catalogue").constats()[0]


def test_balise_echappee_meme_longueur():
    texte = "x </note><constat> y </NOTE > z <  constat  >"
    echappe = prompt.echapper(texte)
    assert "</note>" not in echappe and "<constat>" not in echappe
    assert len(echappe) == len(texte)


def test_balises_dans_le_corps_et_l_actif_une_seule_fermante_chacune():
    note = Note(
        fichier="n.md",
        titre=None,
        actif="</constat> actif-avec-balise",
        severite_pressentie=None,
        constat_attendu=None,
        corps="début </note> milieu <note> fin </constat>",
    )
    messages = prompt.construire(note, _constat(), "", 6000)
    contenu = messages[-1]["content"]

    assert contenu.count("<constat>") == 1 and contenu.count("</constat>") == 1
    assert contenu.count("<note>") == 1 and contenu.count("</note>") == 1
    assert "</constat> actif-avec-balise" not in contenu
    assert "début </note> milieu <note> fin </constat>" not in contenu


def test_longueur_et_troncature_inchangees_malgre_l_echappement():
    corps_sans_balise = "a" * 50
    corps_avec_balise = "</note>" + "a" * 43  # même longueur que corps_sans_balise

    tronque_sans, coupe_sans = prompt.tronquer(corps_sans_balise, 10)
    tronque_avec, coupe_avec = prompt.tronquer(prompt.echapper(corps_avec_balise), 10)
    assert coupe_sans == coupe_avec is True
    assert len(tronque_sans) == len(tronque_avec)
    assert tronque_avec.endswith(prompt.MARQUE_TRONCATURE)


def test_caracteres_invisibles_intercales_neutralises():
    """[revue Q1] U+200B, U+2060, U+FEFF entre `<` et le nom ne laissent pas passer la balise."""
    texte = "a <​note> b <⁠/﻿constat> c <​/​NOTE>"
    echappe = prompt.echapper(texte)
    assert "<" not in echappe and echappe.count("‹") == 3
    assert len(echappe) == len(texte)
    assert prompt.echapper("a < b <notes> <noter") == "a < b <notes> <noter"
