"""Règles pures de relecture (contrats §25 « Règles pures ») : fonctions sans accès disque."""

import pytest

from waveaudit.domaine.modeles import (
    Candidat,
    CodeMotif,
    Cvss,
    EntreeEcartee,
    Fiche,
    Motif,
    Note,
    Reference,
    Statut,
    Tracabilite,
)
from waveaudit.domaine.relecture import (
    EntreeRelecture,
    EtatRelecture,
    FicheCorrigee,
    RefusRelecture,
    corriger,
    fiche_courante,
    rapport_export,
    remplacer_fiche,
    valider,
)

VECTEUR = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
CVSS = Cvss(vecteur=VECTEUR, score=9.8, severite="critique")
REF_1 = Reference(id="CWE-89", titre="Injection SQL", url="https://cwe.mitre.org/data/89")
REF_2 = Reference(id="CWE-20", titre="Validation d'entrée", url="https://cwe.mitre.org/data/20")
CANDIDATS = [Candidat(id="WEB-001", score=3.2), Candidat(id="WEB-002", score=1.1)]
NOTE = Note(
    fichier="01-sqli.md",
    titre="Injection",
    actif=None,
    severite_pressentie=None,
    constat_attendu="WEB-001",
    corps="Paramètre id injectable.",
)
FICHE = Fiche(
    titre="Injection SQL",
    description="d" * 30,
    impact="i" * 30,
    recommandation="r" * 30,
    cvss=CVSS,
    references=[REF_1, REF_2],
    statut=Statut.A_REVOIR,
    motifs=[Motif(code=CodeMotif.REPLI_MOTEUR, detail="x")],
    tracabilite=Tracabilite(
        note="01-sqli.md", constat_id="WEB-001", candidats=CANDIDATS, constat_attendu="WEB-001"
    ),
)


def _corrigee(**champs) -> FicheCorrigee:
    base = {
        "titre": "Injection SQL corrigée",
        "description": "d" * 30,
        "impact": "i" * 30,
        "recommandation": "r" * 30,
        "cvss_vecteur": VECTEUR,
        "cvss": CVSS,
        "references": [REF_1],
    }
    return FicheCorrigee(**(base | champs))


def _entree(**champs) -> EntreeRelecture:
    base = {
        "index": 1,
        "note": "01-sqli.md",
        "source": NOTE,
        "raison_invalide": None,
        "etat": "fiche",
        "candidats": CANDIDATS,
        "candidat_choisi": "WEB-001",
        "fiche_generee": FICHE,
        "fiche_corrigee": None,
        "ecartee": None,
        "statut_relecture": "a_valider",
    }
    return EntreeRelecture(**(base | champs))


def test_fiche_courante_sans_correction():
    assert fiche_courante(_entree()) == FICHE


def test_fiche_courante_garde_statut_motifs_tracabilite_et_cvss_genere_si_corrige_none():
    corrigee = _corrigee(cvss_vecteur="pas un vecteur", cvss=None)
    fiche = fiche_courante(_entree(fiche_corrigee=corrigee))
    assert fiche.titre == corrigee.titre
    assert fiche.references == corrigee.references
    assert fiche.cvss == CVSS  # CVSS généré gardé (brouillon), le corrigé vaut None
    assert fiche.statut == FICHE.statut
    assert fiche.motifs == FICHE.motifs
    assert fiche.tracabilite == FICHE.tracabilite


def test_corriger_cvss_recalcule():
    autre_vecteur = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N"
    resultat = corriger(_entree(), _corrigee(cvss_vecteur=autre_vecteur, cvss=None), 1000)
    assert resultat.fiche_corrigee.cvss is not None
    assert resultat.fiche_corrigee.cvss.vecteur == autre_vecteur
    assert resultat.statut_relecture == "a_valider"


def test_corriger_rubrique_trop_longue_refusee():
    with pytest.raises(RefusRelecture) as exc:
        corriger(_entree(), _corrigee(titre="t" * 30), longueur_max=10)
    assert exc.value.code == "rubrique_trop_longue"


def test_corriger_generation_en_cours_refusee():
    with pytest.raises(RefusRelecture) as exc:
        corriger(_entree(generation="en_cours"), _corrigee(), 1000)
    assert exc.value.code == "generation_en_cours"


def test_corriger_entree_non_fiche_refusee():
    attente = _entree(
        etat="attente",
        candidats=[],
        candidat_choisi=None,
        fiche_generee=None,
        statut_relecture=None,
    )
    with pytest.raises(RefusRelecture) as exc:
        corriger(attente, _corrigee(), 1000)
    assert exc.value.code == "non_modifiable"


def test_corriger_ajout_de_reference_refuse():
    ajoutee = Reference(id="CWE-999", titre="Inconnue", url="https://example.invalid")
    with pytest.raises(RefusRelecture) as exc:
        corriger(_entree(), _corrigee(references=[REF_1, ajoutee]), 1000)
    assert exc.value.code == "reference_ajoutee"


def test_corriger_reference_dupliquee_refusee():
    with pytest.raises(RefusRelecture) as exc:
        corriger(_entree(), _corrigee(references=[REF_1, REF_1]), 1000)
    assert exc.value.code == "reference_dupliquee"


def test_corriger_ordre_des_references_suit_la_fiche_generee():
    # REF_2 puis REF_1 en entrée, alors que fiche_generee.references vaut [REF_1, REF_2].
    resultat = corriger(_entree(), _corrigee(references=[REF_2, REF_1]), 1000)
    assert resultat.fiche_corrigee.references == [REF_1, REF_2]


def test_corriger_identique_sans_increment():
    corrigee = _corrigee()
    entree = corriger(_entree(), corrigee, 1000)
    assert entree.statut_relecture == "a_valider"
    meme = corriger(entree, corrigee, 1000)
    assert meme == entree
    assert meme.version == entree.version


def test_valider_puis_corriger_redevient_a_valider():
    corrigee = _corrigee(cvss=CVSS)
    entree = _entree(fiche_corrigee=corrigee)
    validee = valider(entree)
    assert validee.statut_relecture == "validee"
    modifiee = corriger(validee, _corrigee(titre="Autre titre", cvss=CVSS), 1000)
    assert modifiee.statut_relecture == "a_valider"


def test_valider_vecteur_invalide_refuse():
    entree = _entree(fiche_corrigee=_corrigee(cvss_vecteur="pas un vecteur", cvss=None))
    with pytest.raises(RefusRelecture) as exc:
        valider(entree)
    assert exc.value.code == "vecteur_invalide"


def test_valider_rubrique_vide_refusee():
    entree = _entree(fiche_corrigee=_corrigee(titre="   "))
    with pytest.raises(RefusRelecture) as exc:
        valider(entree)
    assert exc.value.code == "rubrique_vide"


def test_valider_entree_non_fiche_refusee():
    attente = _entree(
        etat="attente",
        candidats=[],
        candidat_choisi=None,
        fiche_generee=None,
        statut_relecture=None,
    )
    with pytest.raises(RefusRelecture) as exc:
        valider(attente)
    assert exc.value.code == "non_modifiable"


def test_valider_generation_en_cours_refusee():
    with pytest.raises(RefusRelecture) as exc:
        valider(_entree(generation="en_cours"))
    assert exc.value.code == "generation_en_cours"


def test_remplacer_fiche():
    entree = _entree(statut_relecture="validee", fiche_corrigee=_corrigee(cvss=CVSS))
    autre_fiche = FICHE.model_copy(update={"titre": "Autre faille"})
    resultat = remplacer_fiche(entree, autre_fiche, "WEB-002", "granite-4.0-1b-q4km")
    assert resultat.fiche_generee == autre_fiche
    assert resultat.fiche_corrigee is None
    assert resultat.candidat_choisi == "WEB-002"
    assert resultat.statut_relecture == "a_valider"
    assert resultat.generation == "aucune"
    assert resultat.erreur_generation is None
    assert resultat.modele_generation == "granite-4.0-1b-q4km"


def test_rapport_export_final_fiches_validees_et_non_validees_en_annexe():
    validee = _entree(index=1, note="01.md", statut_relecture="validee")
    a_valider = _entree(index=2, note="02.md", statut_relecture="a_valider")
    etat = EtatRelecture(
        id_lot="l", langue="fr", modele="m", modele_demande=None, entrees=[validee, a_valider]
    )
    rapport, non_validees = rapport_export(etat, "final")
    assert len(rapport.fiches) == 1
    assert non_validees == frozenset({"02.md"})


def test_rapport_export_brouillon_toutes_les_fiches_et_non_validees():
    validee = _entree(index=1, note="01.md", statut_relecture="validee")
    a_valider = _entree(index=2, note="02.md", statut_relecture="a_valider")
    etat = EtatRelecture(
        id_lot="l", langue="fr", modele="m", modele_demande=None, entrees=[validee, a_valider]
    )
    rapport, non_validees = rapport_export(etat, "brouillon")
    assert len(rapport.fiches) == 2
    assert non_validees == frozenset({"02.md"})


def test_rapport_export_attente_devient_lot_interrompu_dans_les_ecartees():
    attente = _entree(
        index=1,
        note="02-vide.md",
        etat="attente",
        candidats=[],
        candidat_choisi=None,
        fiche_generee=None,
        statut_relecture=None,
    )
    etat = EtatRelecture(
        id_lot="l", langue="fr", modele="m", modele_demande=None, entrees=[attente]
    )
    rapport, _ = rapport_export(etat, "brouillon")
    assert len(rapport.ecartees) == 1
    ecartee = rapport.ecartees[0]
    assert ecartee.statut == Statut.NON_TRAITEE
    assert ecartee.motif.code == CodeMotif.LOT_INTERROMPU
    assert ecartee.constat_attendu == "WEB-001"


def test_rapport_export_attente_sans_source_constat_attendu_none():
    attente = _entree(
        index=1,
        note="02.md",
        source=None,
        raison_invalide="corps vide",
        etat="attente",
        candidats=[],
        candidat_choisi=None,
        fiche_generee=None,
        statut_relecture=None,
    )
    etat = EtatRelecture(
        id_lot="l", langue="fr", modele="m", modele_demande=None, entrees=[attente]
    )
    rapport, _ = rapport_export(etat, "final")
    assert rapport.ecartees[0].constat_attendu is None


def test_rapport_export_ecartees_ordonnees_par_index():
    deja_ecartee = EntreeEcartee(
        note="03.md",
        statut=Statut.NON_RATTACHEE,
        motif=Motif(code=CodeMotif.AUCUN_CONSTAT, detail="x"),
        candidats=[],
        constat_attendu=None,
    )
    entree_ecartee = _entree(
        index=3,
        note="03.md",
        etat="ecartee",
        candidats=[],
        candidat_choisi=None,
        fiche_generee=None,
        statut_relecture=None,
        ecartee=deja_ecartee,
    )
    attente = _entree(
        index=1,
        note="01-attente.md",
        etat="attente",
        candidats=[],
        candidat_choisi=None,
        fiche_generee=None,
        statut_relecture=None,
    )
    fiche_validee = _entree(index=2, note="02.md", statut_relecture="validee")
    etat = EtatRelecture(
        id_lot="l",
        langue="fr",
        modele="m",
        modele_demande=None,
        entrees=[attente, fiche_validee, entree_ecartee],
    )
    rapport, _ = rapport_export(etat, "final")
    assert [e.note for e in rapport.ecartees] == ["01-attente.md", "03.md"]
