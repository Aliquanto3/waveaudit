"""Formes, validations, constantes et motifs du workflow incident (contrats §21, C1)."""

import ipaddress
from datetime import timedelta

import pytest
from pydantic import ValidationError

from tests.incident_outils import HORODATAGE, detection, evenement, recit, regle
from waveaudit.domaine.incident import (
    CHAMPS_LINUX,
    CHAMPS_WINDOWS,
    IDS_REGLES_MINIMAUX,
    LIBELLES_SEVERITE,
    MOTIF_HACHAGE,
    MOTIF_IPV4,
    MOTIF_IPV6,
    MOTIF_TECHNIQUE,
    PROGRAMMES_LINUX,
    SEVERITES,
    TYPES_INDICATEUR,
    Agregation,
    Condition,
    Detection,
    Indicateur,
    LigneIgnoree,
    RapportIncident,
    RequeteIncident,
    schema_recit,
)
from waveaudit.domaine.modeles import CodeMotif, Motif, Statut


def test_fabriques_valides_par_defaut():
    assert recit().detection.evenements == [evenement()]
    assert regle().agregation == Agregation(seuil=5, fenetre_s=300, par=["ip"])


# --- Evenement, LigneIgnoree ----------------------------------------------------------------


@pytest.mark.parametrize("fichier", ["", ".", "..", "a/auth.log", "a\\auth.log", "C:\\x\\a.log"])
def test_fichier_nom_seul(fichier):
    with pytest.raises(ValidationError):
        evenement(fichier=fichier)
    with pytest.raises(ValidationError):
        LigneIgnoree(fichier=fichier, ligne=1, raison="x")


def test_ligne_au_moins_1():
    with pytest.raises(ValidationError):
        evenement(ligne=0)
    with pytest.raises(ValidationError):
        LigneIgnoree(fichier="auth.log", ligne=0, raison="x")
    assert LigneIgnoree(fichier="auth.log", ligne=57, raison="illisible").ligne == 57


def test_horodatage_avec_fuseau():
    with pytest.raises(ValidationError):
        evenement(horodatage=HORODATAGE.replace(tzinfo=None))


def test_evenement_fige_et_extra_interdit():
    with pytest.raises(ValidationError):
        evenement(inconnu=1)
    with pytest.raises(ValidationError):
        evenement().ligne = 2


def test_evenement_cle_et_non_hachable():
    e = evenement(fichier="security.json", ligne=7)
    assert e.cle == ("security.json", 7)
    with pytest.raises(TypeError):
        hash(e)


def test_champs_valeurs_str():
    with pytest.raises(ValidationError):
        evenement(champs={"LogonType": 10})


# --- Condition, Agregation, Regle -------------------------------------------------------------


def test_condition_au_moins_un_critere():
    with pytest.raises(ValidationError):
        Condition()
    with pytest.raises(ValidationError):
        Condition(champs={}, event_id=None)
    assert Condition(event_id=[1102, 104]).event_id == [1102, 104]
    assert Condition(au_moins_un={"Image": "x"}).au_moins_un == {"Image": "x"}


@pytest.mark.parametrize("valeurs", [{"seuil": 1, "fenetre_s": 300}, {"seuil": 5, "fenetre_s": 0}])
def test_agregation_bornes(valeurs):
    with pytest.raises(ValidationError):
        Agregation(**valeurs)
    assert Agregation(seuil=2, fenetre_s=1).par == []


@pytest.mark.parametrize(
    "id_regle", ["INC-WIN", "inc-lin-ssh", "INC-LIN-SSH-", "INC-MAC-X", "INC-LIN-SSH--X", "X"]
)
def test_regle_id_invalide(id_regle):
    with pytest.raises(ValidationError):
        regle(id=id_regle)


def test_regle_prefixe_coherent_avec_source():
    with pytest.raises(ValidationError):
        regle(id="INC-WIN-FORCE-BRUTE")  # source linux
    assert regle(id="INC-WIN-FORCE-BRUTE", source="windows").source == "windows"


def test_regle_references_et_severite():
    with pytest.raises(ValidationError):
        regle(references=[])
    with pytest.raises(ValidationError):
        regle(severite="info")
    assert regle(agregation=None).agregation is None


# --- Detection, Indicateur, Recit ------------------------------------------------------------


def test_detection_periode_et_evenements():
    with pytest.raises(ValidationError):
        detection(debut=HORODATAGE, fin=HORODATAGE - timedelta(seconds=1))
    with pytest.raises(ValidationError):
        Detection(regle_id="X", debut=HORODATAGE, fin=HORODATAGE, hotes=[], evenements=[])
    assert detection().indicateurs == []


def test_indicateur_origines_non_vides():
    with pytest.raises(ValidationError):
        Indicateur(type="ip", valeur="203.0.113.45", origines=[])
    with pytest.raises(ValidationError):
        Indicateur(type="url", valeur="x", origines=["auth.log:1"])
    assert Indicateur(type="hote", valeur="bastion01", origines=["auth.log:1"]).type == "hote"


def test_recit_statut_coherent_avec_motifs():
    motif = Motif(code=CodeMotif.INDICATEUR_RETIRE, detail="203.0.113.254")
    with pytest.raises(ValidationError):
        recit(statut=Statut.A_REVOIR, motifs=[])
    with pytest.raises(ValidationError):
        recit(statut=Statut.OK, motifs=[motif])
    with pytest.raises(ValidationError):
        recit(statut=Statut.NON_TRAITEE)
    assert recit(statut=Statut.A_REVOIR, motifs=[motif]).regle_titre == "Force brute SSH"


def test_rapport_et_requete():
    rapport = RapportIncident(
        debut=None,
        fin=None,
        recits=[],
        indicateurs=[],
        actifs=[],
        recommandations=[],
        sources={"auth.log": 3},
        ignorees=[],
    )
    assert RapportIncident.model_validate_json(rapport.model_dump_json()) == rapport
    assert RequeteIncident(dossier="journaux", annee=2026).modele is None


def test_code_motif_indicateur_retire():
    assert CodeMotif.INDICATEUR_RETIRE.value == "indicateur_retire"


# --- schema_recit, constantes -----------------------------------------------------------------


def test_schema_recit():
    schema = schema_recit(800)
    rubriques = ["titre", "recit", "impact", "recommandation"]
    assert schema["type"] == "object"
    assert schema["required"] == rubriques
    assert schema["additionalProperties"] is False
    assert list(schema["properties"]) == rubriques
    for propriete in schema["properties"].values():
        assert propriete == {"type": "string", "minLength": 1, "maxLength": 800}
    assert "$ref" not in str(schema) and "$defs" not in str(schema)


def test_constantes():
    assert SEVERITES == ("critique", "elevee", "moyenne", "faible")
    assert list(LIBELLES_SEVERITE) == list(SEVERITES)
    assert LIBELLES_SEVERITE["elevee"] == "Élevée"
    assert TYPES_INDICATEUR == tuple(sorted(TYPES_INDICATEUR))
    assert PROGRAMMES_LINUX == {"sshd", "sudo", "useradd"}
    assert len(IDS_REGLES_MINIMAUX) == len(set(IDS_REGLES_MINIMAUX)) == 15
    assert CHAMPS_LINUX == {
        "utilisateur",
        "ip",
        "port",
        "commande",
        "fichier_cible",
        "nouvel_utilisateur",
    }
    assert len(CHAMPS_WINDOWS) == 23
    assert {"IpAddress", "TargetUserName", "Hashes", "CommandLine", "TargetImage"} <= CHAMPS_WINDOWS


# --- Motifs -----------------------------------------------------------------------------------


def _ipv6_valides(texte: str) -> list[str]:
    valides = []
    for candidat in MOTIF_IPV6.findall(texte):
        try:
            ipaddress.IPv6Address(candidat)
        except ValueError:
            continue
        valides.append(candidat)
    return valides


@pytest.mark.parametrize(
    "texte", ["08:02:10", "2026-10-14T08:02:10+02:00", "10.0.17763.1", "0x1010", "T1110.001"]
)
def test_non_mutilation_ni_ip_ni_hachage(texte):
    assert MOTIF_IPV4.findall(texte) == []
    assert _ipv6_valides(texte) == []
    assert MOTIF_HACHAGE.findall(texte) == []


def test_motif_ipv4():
    texte = "depuis 203.0.113.45 port 41001, puis 192.0.2.10 ;"
    assert MOTIF_IPV4.findall(texte) == ["203.0.113.45", "192.0.2.10"]
    assert MOTIF_IPV4.findall("version 1.2.3.4.5") == []


def test_motif_ipv6():
    assert _ipv6_valides("source ::ffff:192.0.2.10 vue") == ["::ffff:192.0.2.10"]
    assert _ipv6_valides("hôte 2001:db8::1 joint") == ["2001:db8::1"]


def test_motif_hachage():
    sha256 = "A1B2C3D4" * 8
    assert MOTIF_HACHAGE.findall(f"SHA256={sha256}") == [sha256]
    assert MOTIF_HACHAGE.findall("MD5=" + "A1B2C3D4" * 4) == ["A1B2C3D4" * 4]
    assert MOTIF_HACHAGE.findall("ab" * 20) == ["ab" * 20]
    assert MOTIF_HACHAGE.findall("ab" * 33) == []  # 66 caractères : aucune longueur admise


def test_motif_technique():
    assert MOTIF_TECHNIQUE.findall("T1110 et t1110.001, T9999, T1110.999") == [
        "T1110",
        "t1110.001",
        "T9999",
        "T1110.999",
    ]
    assert MOTIF_TECHNIQUE.findall("XT1110 T11100 T1110.0011 T1110.") == []
