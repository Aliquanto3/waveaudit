"""Persistance de la relecture (contrats §25 « Persistance », §30 lot.json, AD-19)."""

import json
import re
import shutil
import sys
import threading
from datetime import datetime
from pathlib import Path

import pytest

from waveaudit.application import lot, relecture
from waveaudit.application.config import racine_projet
from waveaudit.application.moteur_demande import MoteurALaDemande, Occupation
from waveaudit.domaine.modeles import (
    Candidat,
    CodeMotif,
    Cvss,
    EntreeEcartee,
    Fiche,
    Motif,
    Note,
    NoteInvalide,
    Rapport,
    Reference,
    RequeteLot,
    Statut,
    Tracabilite,
    TypeEvenement,
)
from waveaudit.domaine.relecture import EtatRelecture, RefusRelecture, corriger, valider
from waveaudit.workflows.fiches.prompt import CONSIGNES

DEMO = racine_projet() / "donnees" / "demo" / "notes"
VECTEUR = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
CVSS = Cvss(vecteur=VECTEUR, score=9.8, severite="critique")
REF = Reference(id="CWE-89", titre="Injection SQL", url="https://cwe.mitre.org/data/89")
CANDIDATS = [Candidat(id="WEB-001", score=3.2), Candidat(id="WEB-002", score=1.1)]
_CONSTAT = re.compile(r"<constat>(.*?)</constat>", re.DOTALL)


@pytest.fixture(autouse=True)
def _pause_courte(monkeypatch):
    monkeypatch.setattr(relecture, "PAUSE_REMPLACEMENT_S", 0.001)


def _note(fichier: str = "01-sqli.md") -> Note:
    return Note(
        fichier=fichier,
        titre="Injection",
        actif=None,
        severite_pressentie=None,
        constat_attendu="WEB-001",
        corps="Paramètre id injectable.",
    )


def _fiche(note: str = "01-sqli.md", constat_id: str = "WEB-001") -> Fiche:
    return Fiche(
        titre="Injection SQL",
        description="d" * 30,
        impact="i" * 30,
        recommandation="r" * 30,
        cvss=CVSS,
        references=[REF],
        statut=Statut.OK,
        motifs=[],
        tracabilite=Tracabilite(
            note=note, constat_id=constat_id, candidats=CANDIDATS, constat_attendu=None
        ),
    )


def _ecartee(note: str, statut: Statut, candidats: list[Candidat]) -> EntreeEcartee:
    code = CodeMotif.AUCUN_CONSTAT if statut == Statut.NON_RATTACHEE else CodeMotif.NOTE_INVALIDE
    return EntreeEcartee(
        note=note,
        statut=statut,
        motif=Motif(code=code, detail="x"),
        candidats=candidats,
        constat_attendu=None,
    )


def _init(dossier: Path, elements, **champs) -> EtatRelecture:
    dossier.mkdir(parents=True, exist_ok=True)
    base = {"id_lot": dossier.name, "langue": "fr", "modele": "externe", "modele_demande": None}
    return relecture.initialiser(dossier, elements=elements, **(base | champs))


def _partiels(dossier: Path) -> list[str]:
    return [p.name for p in dossier.iterdir() if p.name.endswith(".partiel")]


# --- initialiser, enregistrer_resultat, charger ---------------------------------------------


def test_initialiser_une_entree_attente_par_element(tmp_path):
    dossier = tmp_path / "lot-1"
    invalide = NoteInvalide(fichier="02-vide.md", raison="corps vide")
    _init(dossier, [_note(), invalide], langue="en", modele="m", modele_demande="m")
    etat = relecture.charger(dossier)
    assert (etat.id_lot, etat.langue, etat.modele, etat.modele_demande) == (
        "lot-1",
        "en",
        "m",
        "m",
    )
    premiere, seconde = etat.entrees
    assert (premiere.index, premiere.note, premiere.etat) == (1, "01-sqli.md", "attente")
    assert premiere.source == _note() and premiere.version == 1
    assert (seconde.index, seconde.source, seconde.raison_invalide) == (2, None, "corps vide")
    assert _partiels(dossier) == []
    texte = (dossier / relecture.FICHIER).read_text(encoding="utf-8")
    assert EtatRelecture.model_validate_json(texte) == etat


def test_enregistrer_resultat_fiche_et_ecartee(tmp_path):
    dossier = tmp_path / "lot"
    _init(dossier, [_note(), _note("02-x.md")])
    fiche = relecture.enregistrer_resultat(dossier, 1, _fiche())
    assert (fiche.etat, fiche.candidat_choisi, fiche.statut_relecture) == (
        "fiche",
        "WEB-001",
        "a_valider",
    )
    assert fiche.candidats == CANDIDATS and fiche.version == 2
    assert fiche.modele_generation == "externe"
    ecartee = _ecartee("02-x.md", Statut.NON_RATTACHEE, [Candidat(id="AD-1", score=0.0)])
    entree = relecture.enregistrer_resultat(dossier, 2, ecartee)
    assert (entree.etat, entree.ecartee, entree.candidats) == (
        "ecartee",
        ecartee,
        ecartee.candidats,
    )
    assert relecture.charger(dossier).entrees == [fiche, entree]
    assert _partiels(dossier) == []


def test_lot_inconnu(tmp_path):
    with pytest.raises(RefusRelecture) as refus:
        relecture.charger(tmp_path)
    assert refus.value.code == "lot_inconnu"
    lot.ecrire_fiche_lot(
        tmp_path, id_lot="x", workflow="incident", langue=None, modele_demande=None
    )
    with pytest.raises(RefusRelecture, match="relecture") as refus:
        relecture.charger(tmp_path)
    assert refus.value.code == "lot_inconnu"


def test_etat_vide_avec_lot_json(tmp_path):
    lot.ecrire_fiche_lot(
        tmp_path, id_lot=tmp_path.name, workflow="fiches", langue="en", modele_demande="qwen"
    )
    avant = sorted(p.name for p in tmp_path.iterdir())
    etat = relecture.charger(tmp_path)
    assert (etat.entrees, etat.langue, etat.modele, etat.modele_demande) == ([], "en", "", "qwen")
    assert sorted(p.name for p in tmp_path.iterdir()) == avant == ["lot.json"]


def test_ecrire_fiche_lot_sans_effet_si_present(tmp_path):
    lot.ecrire_fiche_lot(tmp_path, id_lot="a", workflow="fiches", langue="fr", modele_demande=None)
    premier = (tmp_path / "lot.json").read_bytes()
    lot.ecrire_fiche_lot(tmp_path, id_lot="b", workflow="incident", langue=None, modele_demande="m")
    assert (tmp_path / "lot.json").read_bytes() == premier
    contenu = json.loads(premier.decode("utf-8"))
    assert set(contenu) == {"id_lot", "workflow", "langue", "modele_demande", "cree_le", "pid"}
    assert datetime.fromisoformat(contenu["cree_le"]).tzinfo is not None
    assert _partiels(tmp_path) == []


def _ecrire_fiches_v010(dossier: Path) -> None:
    dossier.mkdir(parents=True, exist_ok=True)
    rapport = Rapport(
        fiches=[_fiche("b.md"), _fiche("C.md")],
        ecartees=[_ecartee("A.md", Statut.NON_TRAITEE, [])],
    )
    (dossier / "fiches.json").write_text(rapport.model_dump_json(indent=2), encoding="utf-8")
    evenement = {"type": "lot_demarre", "details": {"modele": "granite"}}
    (dossier / "journal.jsonl").write_text(
        "ligne illisible\n" + json.dumps(evenement) + "\n", encoding="utf-8"
    )


def test_charger_repli_fiches_json_sans_ecrire(tmp_path):
    dossier = tmp_path / "v010"
    _ecrire_fiches_v010(dossier)
    etat = relecture.charger(dossier)
    assert (etat.id_lot, etat.langue, etat.modele, etat.modele_demande) == (
        "v010",
        "fr",
        "granite",
        None,
    )
    assert [(e.etat, e.statut_relecture) for e in etat.entrees] == [
        ("ecartee", None),
        ("fiche", "a_valider"),
        ("fiche", "a_valider"),
    ]
    assert all(e.source is None for e in etat.entrees)
    assert not (dossier / relecture.FICHIER).exists()
    # La première modification l'écrit.
    entree = relecture.modifier(dossier, 2, 1, valider)
    assert (entree.statut_relecture, entree.version) == ("validee", 2)
    assert relecture.charger(dossier).entrees[1] == entree
    assert (dossier / relecture.FICHIER).is_file()


def test_rang_stable_v010(tmp_path):
    dossier = tmp_path / "v010"
    _ecrire_fiches_v010(dossier)
    premiere = relecture.charger(dossier)
    assert [(e.index, e.note) for e in premiere.entrees] == [(1, "A.md"), (2, "b.md"), (3, "C.md")]
    assert relecture.charger(dossier) == premiere


# --- modifier ---------------------------------------------------------------------------------


def test_conflit_version(tmp_path):
    dossier = tmp_path / "lot"
    _init(dossier, [_note()])
    relecture.enregistrer_resultat(dossier, 1, _fiche())
    with pytest.raises(RefusRelecture) as refus:
        relecture.modifier(dossier, 1, 1, valider)
    assert refus.value.code == "conflit_version"
    assert relecture.modifier(dossier, 1, 2, valider).version == 3
    with pytest.raises(RefusRelecture) as refus:
        relecture.modifier(dossier, 9, 3, valider)
    assert refus.value.code == "entree_inconnue"


def test_modifier_sans_effet_n_ecrit_pas(tmp_path):
    """Interprétation du §25 (revue R1) : une règle qui renvoie l'entrée telle quelle
    n'incrémente pas la version et n'écrit rien."""
    dossier = tmp_path / "lot"
    _init(dossier, [_note()])
    entree = relecture.enregistrer_resultat(dossier, 1, _fiche())
    avant = (dossier / relecture.FICHIER).read_bytes()
    assert relecture.modifier(dossier, 1, 2, lambda e: e) == entree
    assert (dossier / relecture.FICHIER).read_bytes() == avant


def test_fils_concurrents_lot_et_corrections_sans_perte(tmp_path):
    dossier = tmp_path / "lot"
    notes = [_note(f"{i:02d}.md") for i in range(1, 41)]
    _init(dossier, notes)
    for i in range(1, 21):
        relecture.enregistrer_resultat(dossier, i, _fiche(f"{i:02d}.md"))
    erreurs: list[BaseException] = []

    def lot_() -> None:
        try:
            for i in range(21, 41):
                relecture.enregistrer_resultat(dossier, i, _fiche(f"{i:02d}.md"))
        except BaseException as erreur:  # noqa: BLE001
            erreurs.append(erreur)

    def corrections() -> None:
        try:
            for i in range(1, 21):
                relecture.modifier(dossier, i, 2, valider)
        except BaseException as erreur:  # noqa: BLE001
            erreurs.append(erreur)

    fils = [threading.Thread(target=lot_, daemon=True), threading.Thread(target=corrections)]
    for fil in fils:
        fil.start()
    for fil in fils:
        fil.join(30)
    assert erreurs == [] and not any(fil.is_alive() for fil in fils)
    entrees = relecture.charger(dossier).entrees
    assert all(e.statut_relecture == "validee" and e.version == 3 for e in entrees[:20])
    assert all(e.etat == "fiche" and e.version == 2 for e in entrees[20:])
    assert _partiels(dossier) == []


@pytest.mark.skipif(sys.platform != "win32", reason="verrou de fichier propre à Windows")
def test_fichier_tenu_ouvert_puis_lot_echoue(config_test, tmp_path):
    """[revue A11/E14] relecture.json tenu ouvert par un autre descripteur : réessais, puis
    `lot_echoue` et PermissionError ; aucun provisoire restant."""
    notes = tmp_path / "notes"
    notes.mkdir()
    for nom in sorted(p.name for p in DEMO.iterdir())[:2]:
        shutil.copy(DEMO / nom, notes)
    tenus = []

    def abonne(evenement) -> None:
        if evenement.type == TypeEvenement.LOT_DEMARRE:
            sortie = config_test.chemins.var / "sorties" / "lot-tenu"
            tenus.append((sortie / relecture.FICHIER).open("rb"))

    try:
        with pytest.raises(PermissionError):
            lot.executer_lot(RequeteLot(dossier=notes, id_lot="lot-tenu"), config_test, abonne)
    finally:
        for fichier in tenus:
            fichier.close()
    sortie = config_test.chemins.var / "sorties" / "lot-tenu"
    lignes = (sortie / "journal.jsonl").read_text(encoding="utf-8").splitlines()
    echec = json.loads(lignes[-1])
    assert echec["type"] == TypeEvenement.LOT_ECHOUE
    assert echec["details"]["message"] == lot.MESSAGE_ECRITURE_RELECTURE
    assert _partiels(sortie) == []
    assert all(e.etat == "attente" for e in relecture.charger(sortie).entrees)


def test_os_replace_en_echec_puis_erreur(tmp_path, monkeypatch):
    dossier = tmp_path / "lot"
    _init(dossier, [_note()])
    avant = (dossier / relecture.FICHIER).read_bytes()
    essais = []

    def refuse(source, cible):
        essais.append(cible)
        raise PermissionError(13, "accès refusé")

    monkeypatch.setattr(relecture.os, "replace", refuse)
    with pytest.raises(PermissionError):
        relecture.enregistrer_resultat(dossier, 1, _fiche())
    assert len(essais) == relecture.ESSAIS_REMPLACEMENT == 10
    assert (dossier / relecture.FICHIER).read_bytes() == avant
    assert _partiels(dossier) == []


# --- demarrer_regeneration --------------------------------------------------------------------


def _lot_fiche(dossier: Path) -> None:
    _init(dossier, [_note(), _note("02-x.md"), NoteInvalide(fichier="03.md", raison="vide")])
    relecture.enregistrer_resultat(dossier, 1, _fiche())


def test_ordre_des_refus_demarrer_regeneration(tmp_path):
    dossier = tmp_path / "lot"
    _lot_fiche(dossier)
    relecture.enregistrer_resultat(dossier, 3, _ecartee("03.md", Statut.NON_TRAITEE, []))

    def code(index, version, constat_id="WEB-002", confirmer=False, **kw) -> str:
        with pytest.raises(RefusRelecture) as refus:
            relecture.demarrer_regeneration(dossier, index, version, constat_id, confirmer, **kw)
        return refus.value.code

    en_cours = relecture.demarrer_regeneration(dossier, 1, 2, "WEB-002", False)
    assert (en_cours.generation, en_cours.version) == ("en_cours", 3)
    occupation = Occupation("regeneration", "lot", 1, datetime(2026, 1, 1))
    # conflit_version avant generation_en_cours.
    assert code(1, 2, occupation=occupation) == "conflit_version"
    assert code(1, 3, occupation=occupation) == "generation_en_cours"
    # Entrée attente, puis écartée non_traitee : non_generable.
    assert code(2, 1) == "non_generable"
    assert code(3, 2) == "non_generable"


def test_candidat_courant(tmp_path):
    dossier = tmp_path / "lot"
    _lot_fiche(dossier)
    with pytest.raises(RefusRelecture) as refus:
        relecture.demarrer_regeneration(dossier, 1, 2, "WEB-001", True)
    assert refus.value.code == "candidat_courant"


def test_candidat_inconnu_hors_candidats_d_une_fiche(tmp_path):
    dossier = tmp_path / "lot"
    _lot_fiche(dossier)
    with pytest.raises(RefusRelecture) as refus:
        relecture.demarrer_regeneration(dossier, 1, 2, "AD-999", True, ids_catalogue={"AD-999"})
    assert refus.value.code == "candidat_inconnu"


def test_source_absente(tmp_path):
    dossier = tmp_path / "v010"
    _ecrire_fiches_v010(dossier)
    with pytest.raises(RefusRelecture) as refus:
        relecture.demarrer_regeneration(dossier, 2, 1, "WEB-002", True)
    assert refus.value.code == "source_absente"
    assert not (dossier / relecture.FICHIER).exists()


def test_confirmation_fiche_validee(tmp_path):
    dossier = tmp_path / "lot"
    _lot_fiche(dossier)
    relecture.modifier(dossier, 1, 2, valider)
    with pytest.raises(RefusRelecture) as refus:
        relecture.demarrer_regeneration(dossier, 1, 3, "WEB-002", False)
    assert refus.value.code == "confirmation_requise"
    entree = relecture.demarrer_regeneration(dossier, 1, 3, "WEB-002", True)
    assert entree.generation == "en_cours"


def test_confirmation_fiche_corrigee(tmp_path):
    from waveaudit.domaine.relecture import FicheCorrigee

    dossier = tmp_path / "lot"
    _lot_fiche(dossier)
    correction = FicheCorrigee(
        titre="Autre titre",
        description="d" * 30,
        impact="i" * 30,
        recommandation="r" * 30,
        cvss_vecteur=VECTEUR,
        cvss=CVSS,
        references=[REF],
    )
    relecture.modifier(dossier, 1, 2, lambda e: corriger(e, correction, 4000))
    with pytest.raises(RefusRelecture) as refus:
        relecture.demarrer_regeneration(dossier, 1, 3, "WEB-002", False)
    assert refus.value.code == "confirmation_requise"


def test_lecture_n_ecrit_pas_generation_interrompue(tmp_path):
    dossier = tmp_path / "lot"
    _lot_fiche(dossier)
    relecture.demarrer_regeneration(dossier, 1, 2, "WEB-002", False)
    avant = (dossier / relecture.FICHIER).read_bytes()
    entree = relecture.charger(dossier).entrees[0]
    assert (entree.generation, entree.erreur_generation, entree.version) == (
        "echec",
        relecture.GENERATION_INTERROMPUE,
        3,
    )
    occupation = Occupation("regeneration", "lot", 1, datetime(2026, 1, 1))
    assert relecture.charger(dossier, occupation=occupation).entrees[0].generation == "en_cours"
    autre = Occupation("regeneration", "lot", 2, datetime(2026, 1, 1))
    assert relecture.charger(dossier, occupation=autre).entrees[0].generation == "echec"
    assert (dossier / relecture.FICHIER).read_bytes() == avant
    # Une modification de l'entrée interrompue repart de l'état présenté.
    relance = relecture.demarrer_regeneration(dossier, 1, 3, "WEB-002", False)
    assert (relance.generation, relance.version) == ("en_cours", 4)


# --- regenerer (faux moteur, mode externe) ----------------------------------------------------


@pytest.fixture
def moteurs():
    ouverts: list[MoteurALaDemande] = []

    def fabrique(config) -> MoteurALaDemande:
        moteur = MoteurALaDemande(config)
        ouverts.append(moteur)
        return moteur

    yield fabrique
    for moteur in ouverts:
        moteur.fermer()


def _vers(config, fm):
    return config.model_copy(
        update={"moteur": config.moteur.model_copy(update={"base_url": fm.base_url})}
    )


def _lot_reel(config, dossier: Path, moteurs, **champs):
    """Lot d'une note de démonstration traitée par le vrai pipeline et le faux moteur."""
    from waveaudit.workflows.fiches import pipeline

    with moteurs(config).utiliser(None) as (ports, _info):
        (note,) = [n for n in ports.source_notes.lire(DEMO) if n.fichier.startswith("03-")]
        resultat = pipeline.creer(config, ports).traiter(note)
        ids = [c.id for c in ports.catalogue.constats()]
    assert isinstance(resultat, Fiche)
    _init(dossier, [note], **champs)
    relecture.enregistrer_resultat(dossier, 1, resultat)
    return note, resultat, ids


def test_regeneration_externe_nouveau_constat(config_test, faux_moteur, tmp_path, moteurs):
    fm = faux_moteur()
    config = _vers(config_test, fm)
    dossier = tmp_path / "lot"
    _, fiche, _ = _lot_reel(config, dossier, moteurs, modele_demande="modele-b")
    nouvel = fiche.tracabilite.candidats[1].id
    relecture.demarrer_regeneration(dossier, 1, 2, nouvel, False)
    fm.requetes.clear()
    relecture.regenerer(config, dossier, 1, nouvel, moteurs(config))

    entree = relecture.charger(dossier).entrees[0]
    assert (entree.etat, entree.generation, entree.candidat_choisi) == ("fiche", "aucune", nouvel)
    assert entree.version == 4 and entree.statut_relecture == "a_valider"
    # Nouveau constat_id dans <constat>, garde-fous appliqués, modèle résolu du lot.
    (requete,) = fm.requetes
    assert requete["model"] == "modele-b"
    dernier = requete["messages"][-1]["content"]
    assert json.loads(_CONSTAT.search(dernier).group(1))["id"] == nouvel
    assert entree.fiche_generee.tracabilite.constat_id == nouvel
    assert entree.fiche_generee.tracabilite.candidats == fiche.tracabilite.candidats
    # Aucun événement écrit.
    assert not (dossier / "journal.jsonl").exists()
    assert _partiels(dossier) == []


def test_modele_generation_consigne(config_test, faux_moteur, tmp_path, moteurs):
    fm = faux_moteur()
    config = _vers(config_test, fm)
    dossier = tmp_path / "lot"
    _, fiche, _ = _lot_reel(config, dossier, moteurs, modele="externe", modele_demande="mod-x")
    nouvel = fiche.tracabilite.candidats[1].id
    relecture.demarrer_regeneration(dossier, 1, 2, nouvel, False)
    relecture.regenerer(config, dossier, 1, nouvel, moteurs(config))
    assert relecture.charger(dossier).entrees[0].modele_generation == "mod-x"


def test_regeneration_dans_la_langue_du_lot(config_test, faux_moteur, tmp_path, moteurs):
    fm = faux_moteur()
    config = _vers(config_test, fm)
    dossier = tmp_path / "lot"
    _, fiche, _ = _lot_reel(config, dossier, moteurs, langue="en")
    assert config.fiches.langue == "fr"
    nouvel = fiche.tracabilite.candidats[1].id
    relecture.demarrer_regeneration(dossier, 1, 2, nouvel, False)
    fm.requetes.clear()
    relecture.regenerer(config, dossier, 1, nouvel, moteurs(config))
    (requete,) = fm.requetes
    contenus = " ".join(m["content"] for m in requete["messages"])
    assert CONSIGNES["en"] in contenus and CONSIGNES["fr"] not in contenus


def test_non_rattachee_id_du_catalogue(config_test, faux_moteur, tmp_path, moteurs):
    fm = faux_moteur()
    config = _vers(config_test, fm)
    dossier = tmp_path / "lot"
    note, fiche, ids = _lot_reel(config, dossier, moteurs)
    # Entrée 1 réécrite en non_rattachee (candidats à score nul).
    nuls = [Candidat(id=c.id, score=0.0) for c in fiche.tracabilite.candidats]
    relecture.enregistrer_resultat(dossier, 1, _ecartee(note.fichier, Statut.NON_RATTACHEE, nuls))
    choisi = next(i for i in ids if i not in {c.id for c in nuls})
    with pytest.raises(RefusRelecture) as refus:
        relecture.demarrer_regeneration(dossier, 1, 3, "INCONNU-1", False, ids_catalogue=ids)
    assert refus.value.code == "candidat_inconnu"
    with pytest.raises(RefusRelecture) as refus:
        relecture.demarrer_regeneration(dossier, 1, 3, choisi, False)
    assert refus.value.code == "candidat_inconnu"
    relecture.demarrer_regeneration(dossier, 1, 3, choisi, False, ids_catalogue=ids)
    relecture.regenerer(config, dossier, 1, choisi, moteurs(config))
    entree = relecture.charger(dossier).entrees[0]
    assert (entree.etat, entree.candidat_choisi, entree.ecartee) == ("fiche", choisi, None)
    assert (
        EtatRelecture.model_validate_json(
            (dossier / relecture.FICHIER).read_text(encoding="utf-8")
        ).entrees[0]
        == entree
    )


def test_repli_moteur_garde_la_fiche(config_test, faux_moteur, tmp_path, moteurs):
    dossier = tmp_path / "lot"
    _, fiche, _ = _lot_reel(_vers(config_test, faux_moteur()), dossier, moteurs)
    nouvel = fiche.tracabilite.candidats[1].id
    relecture.demarrer_regeneration(dossier, 1, 2, nouvel, False)
    en_panne = _vers(config_test, faux_moteur("erreur_500"))
    relecture.regenerer(en_panne, dossier, 1, nouvel, moteurs(en_panne))
    entree = relecture.charger(dossier).entrees[0]
    assert (entree.generation, entree.erreur_generation) == ("echec", relecture.MOTEUR_MUET)
    assert entree.fiche_generee == fiche and entree.candidat_choisi == fiche.tracabilite.constat_id


def test_echec_ouverture_generation_echec(config_test, faux_moteur, tmp_path, moteurs):
    dossier = tmp_path / "lot"
    _, fiche, _ = _lot_reel(_vers(config_test, faux_moteur()), dossier, moteurs)
    nouvel = fiche.tracabilite.candidats[1].id
    relecture.demarrer_regeneration(dossier, 1, 2, nouvel, False)
    coupe = _vers(config_test, faux_moteur("injoignable"))
    relecture.regenerer(coupe, dossier, 1, nouvel, moteurs(coupe))
    entree = relecture.charger(dossier).entrees[0]
    assert entree.generation == "echec" and entree.erreur_generation
    assert str(tmp_path) not in entree.erreur_generation
    assert entree.fiche_generee == fiche


def test_toute_exception_donne_echec(config_test, tmp_path, monkeypatch, moteurs):
    from waveaudit.workflows.fiches import pipeline

    dossier = tmp_path / "lot"
    _lot_fiche(dossier)
    relecture.demarrer_regeneration(dossier, 1, 2, "WEB-002", False)

    def plante(config, ports):
        raise RuntimeError(f"panne dans {tmp_path / 'x.txt'}")

    monkeypatch.setattr(pipeline, "creer", plante)
    relecture.regenerer(config_test, dossier, 1, "WEB-002", moteurs(config_test))
    entree = relecture.charger(dossier).entrees[0]
    assert (entree.generation, entree.erreur_generation) == ("echec", "panne dans x.txt")
