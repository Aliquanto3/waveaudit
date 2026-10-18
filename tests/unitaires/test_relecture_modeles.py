"""Formes de relecture (contrats §25 « Formes ») : invariants et aller-retour JSON."""

import pytest
from pydantic import ValidationError

from waveaudit.domaine.erreurs import EntreeInvalide
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
)

VECTEUR = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
CVSS = Cvss(vecteur=VECTEUR, score=9.8, severite="critique")
REFERENCE = Reference(id="CWE-89", titre="Injection SQL", url="https://cwe.mitre.org/data/89")
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
    references=[REFERENCE],
    statut=Statut.OK,
    motifs=[],
    tracabilite=Tracabilite(
        note="01-sqli.md", constat_id="WEB-001", candidats=CANDIDATS, constat_attendu="WEB-001"
    ),
)
CORRIGEE = FicheCorrigee(
    titre="Injection SQL corrigée",
    description="d" * 30,
    impact="i" * 30,
    recommandation="r" * 30,
    cvss_vecteur="pas un vecteur",
    cvss=None,
    references=[],
)
ECARTEE = EntreeEcartee(
    note="02-vide.md",
    statut=Statut.NON_RATTACHEE,
    motif=Motif(code=CodeMotif.AUCUN_CONSTAT, detail="aucun constat"),
    candidats=[Candidat(id="WEB-003", score=0.0)],
    constat_attendu=None,
)


def _entree(**champs) -> dict:
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
    return base | champs


def _attente(**champs) -> dict:
    return (
        _entree(
            etat="attente",
            candidats=[],
            candidat_choisi=None,
            fiche_generee=None,
            statut_relecture=None,
        )
        | champs
    )


def test_defauts():
    entree = EntreeRelecture(**_entree())
    assert entree.generation == "aucune"
    assert entree.erreur_generation is None
    assert entree.modele_generation is None
    assert entree.version == 1
    etat = EtatRelecture(id_lot="l", langue="fr", modele="m", modele_demande=None, entrees=[])
    assert etat.version_schema == 1


def test_entree_valide_par_etat():
    EntreeRelecture(**_attente())
    EntreeRelecture(**_entree(fiche_corrigee=CORRIGEE, statut_relecture="validee"))
    EntreeRelecture(
        **_attente(etat="ecartee", note="02-vide.md", ecartee=ECARTEE, candidats=ECARTEE.candidats)
    )
    EntreeRelecture(
        **_attente(source=None, raison_invalide="corps vide", etat="ecartee", ecartee=ECARTEE)
    )


@pytest.mark.parametrize(
    "champs",
    [
        {"fiche_generee": None},  # fiche sans fiche_generee
        {"statut_relecture": None},  # fiche sans statut de relecture
        {"etat": "attente"},  # fiche_generee hors de l'état fiche
        {"ecartee": ECARTEE},  # ecartee renseignée en état fiche
        {"candidat_choisi": "WEB-999"},  # hors candidats, candidats de score > 0
        {"index": 0},
        {"version": 0},
        {"generation": "inconnue"},
        {"statut_relecture": "refusee"},
        {"champ_inconnu": 1},
    ],
)
def test_invariants_refuses(champs):
    with pytest.raises(ValidationError):
        EntreeRelecture(**_entree(**champs))


def test_ecartee_sans_entree_ecartee_refusee():
    with pytest.raises(ValidationError):
        EntreeRelecture(**_attente(etat="ecartee"))


def test_fiche_corrigee_exige_etat_fiche():
    with pytest.raises(ValidationError):
        EntreeRelecture(**_attente(fiche_corrigee=CORRIGEE))


def test_candidat_hors_candidats_tolere_pour_non_rattachee():
    """[revue A14] Fiche générée depuis non_rattachee : constat choisi dans tout le catalogue."""
    entree = EntreeRelecture(
        **_entree(candidats=ECARTEE.candidats, candidat_choisi="CRYPTO-004", note="02-vide.md")
    )
    assert entree.candidat_choisi == "CRYPTO-004"
    # Mais pas pour une entrée encore écartée.
    with pytest.raises(ValidationError):
        EntreeRelecture(
            **_attente(
                etat="ecartee",
                ecartee=ECARTEE,
                candidats=ECARTEE.candidats,
                candidat_choisi="CRYPTO-004",
            )
        )


def test_vecteur_corrige_borne_a_100():
    with pytest.raises(ValidationError):
        FicheCorrigee.model_validate(CORRIGEE.model_dump() | {"cvss_vecteur": "x" * 101})
    assert FicheCorrigee.model_validate(CORRIGEE.model_dump() | {"cvss_vecteur": "x" * 100})


def test_formes_figees():
    entree = EntreeRelecture(**_entree())
    with pytest.raises(ValidationError):
        entree.version = 2


def test_entrees_triees_par_index():
    une = EntreeRelecture(**_attente(index=1))
    deux = EntreeRelecture(**_attente(index=2, note="02.md"))
    EtatRelecture(id_lot="l", langue="en", modele="m", modele_demande=None, entrees=[une, deux])
    with pytest.raises(ValidationError):
        EtatRelecture(id_lot="l", langue="fr", modele="m", modele_demande=None, entrees=[deux, une])
    with pytest.raises(ValidationError):
        EtatRelecture(id_lot="l", langue="de", modele="m", modele_demande=None, entrees=[])


def test_aller_retour_json():
    etat = EtatRelecture(
        id_lot="20261018-120000",
        langue="en",
        modele="granite-4.0-1b-q4km",
        modele_demande="qwen3.5-0.8b-q4km",
        entrees=[
            EntreeRelecture(
                **_entree(
                    fiche_corrigee=CORRIGEE,
                    generation="echec",
                    erreur_generation="génération interrompue",
                    modele_generation="granite-4.0-1b-q4km",
                    version=4,
                )
            ),
            EntreeRelecture(
                **_attente(
                    index=2,
                    note="02-vide.md",
                    etat="ecartee",
                    ecartee=ECARTEE,
                    candidats=ECARTEE.candidats,
                )
            ),
            EntreeRelecture(**_attente(index=3, note="03.md", source=None, raison_invalide="x")),
        ],
    )
    texte = etat.model_dump_json(indent=2)
    assert EtatRelecture.model_validate_json(texte) == etat


def test_refus_relecture():
    refus = RefusRelecture("conflit_version", "La fiche a changé entre-temps.")
    assert isinstance(refus, EntreeInvalide)
    assert refus.code == "conflit_version"
    assert refus.message == str(refus) == "La fiche a changé entre-temps."
