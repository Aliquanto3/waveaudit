import json
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from waveaudit.domaine import erreurs
from waveaudit.domaine.cvss31 import metriques_depuis_vecteur, vecteur
from waveaudit.domaine.erreurs import EntreeInvalide
from waveaudit.domaine.modeles import (
    LANGUES,
    Candidat,
    CodeMotif,
    ConstatType,
    Cvss,
    EntreeEcartee,
    EvenementLot,
    Fiche,
    MetriquesCvss,
    Motif,
    Note,
    Rapport,
    Reference,
    RequeteLot,
    Statut,
    TextesConstat,
    Tracabilite,
    TypeEvenement,
    schema_sortie,
)
from waveaudit.workflows.registre import REGISTRE

VECTEUR = "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N"


def _fiche(statut: Statut = Statut.OK, motifs: list[Motif] | None = None) -> Fiche:
    return Fiche(
        titre="t",
        description="d",
        impact="i",
        recommandation="r",
        cvss=Cvss(vecteur=VECTEUR, score=6.1, severite="moyenne"),
        references=[Reference(id="CWE-79", titre="XSS", url="https://cwe.mitre.org/x")],
        statut=statut,
        motifs=motifs or [],
        tracabilite=Tracabilite(
            note="01-xss.md",
            constat_id="WEB-XSS-REFLECHI",
            candidats=[Candidat(id="WEB-XSS-REFLECHI", score=3.2)],
            constat_attendu=None,
        ),
    )


def _parcourir(noeud):
    yield noeud
    if isinstance(noeud, dict):
        for valeur in noeud.values():
            yield from _parcourir(valeur)
    elif isinstance(noeud, list):
        for valeur in noeud:
            yield from _parcourir(valeur)


def test_schema_sortie_sans_ref_et_ferme():
    schema = schema_sortie(1200)
    texte = json.dumps(schema)
    assert "$ref" not in texte and "$defs" not in texte and "references" not in texte
    objets = [n for n in _parcourir(schema) if isinstance(n, dict) and n.get("type") == "object"]
    assert len(objets) == 2
    for objet in objets:
        assert objet["additionalProperties"] is False
        assert objet["required"] == list(objet["properties"])
    assert list(schema["properties"]) == [
        "titre",
        "description",
        "impact",
        "recommandation",
        "cvss",
    ]
    for rubrique in ("titre", "description", "impact", "recommandation"):
        assert schema["properties"][rubrique] == {
            "type": "string",
            "minLength": 1,
            "maxLength": 1200,
        }


def test_schema_sortie_enums_cvss():
    metriques = schema_sortie(50)["properties"]["cvss"]["properties"]
    assert {nom: m["enum"] for nom, m in metriques.items()} == {
        "AV": ["N", "A", "L", "P"],
        "AC": ["L", "H"],
        "PR": ["N", "L", "H"],
        "UI": ["N", "R"],
        "S": ["U", "C"],
        "C": ["N", "L", "H"],
        "I": ["N", "L", "H"],
        "A": ["N", "L", "H"],
    }
    assert all(m["type"] == "string" for m in metriques.values())


def test_extra_interdit_et_gele():
    with pytest.raises(ValidationError):
        Reference(id="CWE-79", titre="t", url="https://x", inconnu=1)
    reference = Reference(id="CWE-79", titre="t", url="https://x")
    with pytest.raises(ValidationError):
        reference.id = "autre"


def test_note_regles():
    commun = dict(titre=None, actif=None, severite_pressentie=None, constat_attendu=None)
    Note(fichier="01-a.md", corps="texte", **commun)
    with pytest.raises(ValidationError):
        Note(fichier="01-a.md", corps="  \n", **commun)
    with pytest.raises(ValidationError):
        Note(fichier="dossier/01-a.md", corps="texte", **commun)
    with pytest.raises(ValidationError):
        Note(fichier="01-a.md", corps="texte", **(commun | {"severite_pressentie": "haute"}))


def test_constat_type_au_moins_une_reference():
    champs = dict(
        id="WEB-X",
        titre="t",
        famille="web",
        mots_cles=["x"],
        description="d",
        impact="i",
        recommandation="r",
        cvss_vecteur=VECTEUR,
        source="rédaction propre",
    )
    with pytest.raises(ValidationError):
        ConstatType(references=[], **champs)
    with pytest.raises(ValidationError):
        ConstatType(
            references=[Reference(id="a", titre="b", url="c")], **(champs | {"famille": "x"})
        )


def test_fiche_statut_et_motifs():
    _fiche()
    _fiche(Statut.A_REVOIR, [Motif(code=CodeMotif.REPLI_MOTEUR, detail="x")])
    with pytest.raises(ValidationError):
        _fiche(Statut.A_REVOIR)
    with pytest.raises(ValidationError):
        _fiche(Statut.OK, [Motif(code=CodeMotif.VECTEUR_INVALIDE, detail="x")])
    with pytest.raises(ValidationError):
        _fiche(Statut.NON_TRAITEE)


def test_rapport_aller_retour_json():
    ecartee = EntreeEcartee(
        note="hors-sujet.md",
        statut=Statut.NON_RATTACHEE,
        motif=Motif(code=CodeMotif.AUCUN_CONSTAT, detail="score 0"),
        candidats=[],
        constat_attendu=None,
    )
    rapport = Rapport(fiches=[_fiche()], ecartees=[ecartee])
    donnees = rapport.model_dump(mode="json")
    assert donnees["fiches"][0]["statut"] == "ok"
    assert donnees["ecartees"][0]["statut"] == "non_rattachee"
    assert Rapport.model_validate(json.loads(json.dumps(donnees))) == rapport
    assert Rapport.model_validate_json(rapport.model_dump_json()) == rapport


def test_evenement_horodatage_avec_fuseau():
    evenement = EvenementLot(
        type=TypeEvenement.LOT_DEMARRE,
        horodatage=datetime.now().astimezone(),
        index=None,
        total=20,
        note=None,
        statut=None,
        duree_s=None,
        details={"id_lot": "20261017-120000", "modele": "m", "pid_moteur": None},
    )
    assert json.loads(evenement.model_dump_json())["type"] == "lot_demarre"
    with pytest.raises(ValidationError):
        EvenementLot(
            type=TypeEvenement.LOT_TERMINE,
            horodatage=datetime(2026, 10, 17),
            index=None,
            total=0,
            note=None,
            statut=None,
            duree_s=None,
        )
    sans_details = EvenementLot(
        type=TypeEvenement.LOT_TERMINE,
        horodatage=datetime(2026, 10, 17, tzinfo=UTC),
        index=None,
        total=0,
        note=None,
        statut=None,
        duree_s=None,
    )
    assert sans_details.details == {}


def test_erreurs_hors_oserror():
    for nom in (
        "EntreeInvalide",
        "ConfigurationInvalide",
        "MoteurInjoignable",
        "SortieInvalide",
        "ConnexionInterdite",
        "EmpreinteInvalide",
    ):
        classe = getattr(erreurs, nom)
        assert issubclass(classe, erreurs.ErreurWaveAudit)
        assert not issubclass(classe, OSError)


def test_cvss31_aller_retour():
    metriques = metriques_depuis_vecteur(VECTEUR)
    assert metriques == MetriquesCvss(AV="N", AC="L", PR="N", UI="R", S="C", C="L", I="L", A="N")
    assert vecteur(metriques) == VECTEUR


@pytest.mark.parametrize(
    "invalide",
    [
        "AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N",
        "CVSS:3.0/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N",
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L",
        "CVSS:3.1/AV:X/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N",
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N/E:F",
        "CVSS:3.1/AV:N/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L",
    ],
)
def test_cvss31_vecteur_invalide(invalide):
    with pytest.raises(EntreeInvalide):
        metriques_depuis_vecteur(invalide)


def test_registre_fiches():
    assert list(REGISTRE) == ["fiches"]
    assert callable(REGISTRE["fiches"])


# --- v2 (contrats §1 v2, story S0) ---

_CONSTAT_V2 = dict(
    id="WEB-X",
    titre="Titre français",
    famille="web",
    mots_cles=["x"],
    description="Description française.",
    impact="Impact français.",
    recommandation="Recommandation française.",
    cvss_vecteur=VECTEUR,
    references=[Reference(id="CWE-79", titre="XSS", url="https://cwe.mitre.org/x")],
    source="test",
)


def test_langues():
    assert LANGUES == ("fr", "en")


def test_textes_francais_depuis_les_champs_racine():
    constat = ConstatType(**_CONSTAT_V2)
    assert constat.en is None
    assert constat.textes("fr") == TextesConstat(
        titre="Titre français",
        description="Description française.",
        impact="Impact français.",
        recommandation="Recommandation française.",
    )


def test_textes_anglais_leve_si_en_vaut_none():
    with pytest.raises(ValueError):
        ConstatType(**_CONSTAT_V2).textes("en")


def test_textes_anglais():
    en = TextesConstat(titre="Title", description="D.", impact="I.", recommandation="R.")
    constat = ConstatType(**_CONSTAT_V2, en=en)
    assert constat.textes("en") == en
    assert constat.textes("fr").titre == "Titre français"


@pytest.mark.parametrize("vide", ["", "   "])
def test_textes_constat_non_vides(vide):
    with pytest.raises(ValidationError):
        TextesConstat(titre=vide, description="d", impact="i", recommandation="r")
    with pytest.raises(ValidationError):
        TextesConstat(titre="t", description="d", impact="i", recommandation="r", autre="x")


def test_nouveaux_codes_motif():
    assert CodeMotif.REPETITION == "repetition"
    assert CodeMotif.LANGUE == "langue"
    assert CodeMotif.LOT_INTERROMPU == "lot_interrompu"
    assert CodeMotif.INDICATEUR_RETIRE == "indicateur_retire"


def test_requete_lot_langue():
    assert RequeteLot(dossier="notes").langue is None
    assert RequeteLot(dossier="notes", langue="en").langue == "en"
    with pytest.raises(ValidationError):
        RequeteLot(dossier="notes", langue="de")
