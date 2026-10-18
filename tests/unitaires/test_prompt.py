"""Échappement des balises `note`/`constat` dans le prompt des fiches (contrats §8, CAP-2)."""

import json
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


def test_langue_en_consigne_et_constat_anglais_asset():
    """[v2] CAP-8 (contrats §8, §23) : consigne anglaise, textes du constat en anglais."""
    constat = _constat()
    note = Note(
        fichier="n.md",
        titre=None,
        actif="app.exemple.test",
        severite_pressentie=None,
        constat_attendu=None,
        corps="corps",
    )
    messages = prompt.construire(note, constat, "", 6000, langue="en")

    assert messages[0]["content"] == prompt.CONSIGNES["en"]
    assert "Rédige" not in messages[0]["content"]
    contenu = messages[1]["content"]
    assert contenu.startswith("<constat>")
    assert "Asset: app.exemple.test" in contenu
    debut, fin = contenu.index("<constat>"), contenu.index("</constat>")
    donnees = json.loads(contenu[debut + len("<constat>") : fin])
    assert donnees["titre"] == constat.en.titre
    assert donnees["description"] == constat.en.description


def test_langue_fr_defaut_consigne_francaise():
    """Sans `langue`, la consigne et les textes restent ceux de la v0.1.0 (français)."""
    constat = _constat()
    note = Note(
        fichier="n.md",
        titre=None,
        actif=None,
        severite_pressentie=None,
        constat_attendu=None,
        corps="corps",
    )
    messages = prompt.construire(note, constat, "", 6000)
    assert messages[0]["content"] == prompt.CONSIGNE == prompt.CONSIGNES["fr"]


def test_consigne_revisee_cap6_fr_et_en_paralleles():
    """Q5 (CAP-6) : consigne révisée par rubrique, mêmes exigences en français et en anglais."""
    fr, en = prompt.CONSIGNES["fr"], prompt.CONSIGNES["en"]
    # Mêmes puces, dans le même ordre : une par rubrique, puis les trois règles du §8.
    puces_fr = [ligne.split(" ")[1] for ligne in fr.splitlines()[1:]]
    puces_en = [ligne.split(" ")[1].rstrip(":") for ligne in en.splitlines()[1:]]
    assert puces_fr[:4] == ["titre", "description", "impact", "recommandation"]
    assert [p.rstrip(":") for p in puces_fr[:4]] == puces_en[:4]
    assert len(fr.splitlines()) == len(en.splitlines()) == 8
    # Contre la recopie : titre et impact propres au cas, description non recopiée.
    assert "ne reprends pas le titre du constat type" in fr
    assert "ne recopie pas la description générique" in fr
    assert "ne recopie pas l'impact générique" in fr
    assert "do not reuse the constat type's title" in en
    assert "do not copy the generic description" in en
    assert "do not copy the generic impact" in en
    # Règles du §8 gardées dans les deux langues, et langue de rédaction demandée.
    regles = {
        "fr": ("N'invente aucun", "vecteur CVSS par défaut", "objet JSON", "en français"),
        "en": ("Do not invent any", "default CVSS vector", "JSON object", "professional English"),
    }
    for langue, attendus in regles.items():
        assert all(attendu in prompt.CONSIGNES[langue] for attendu in attendus)
    assert "<constat>" in fr and "<note>" in fr and "<constat>" in en and "<note>" in en
