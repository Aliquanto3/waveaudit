"""Catalogue de règles et sa vérification (CAP-2, contrats §21 « Règles », C3)."""

from pathlib import Path

import pytest

from tests.incident_outils import regle
from waveaudit.adaptateurs.regles_yaml import CatalogueReglesYaml, verifier_regles
from waveaudit.domaine.erreurs import ConfigurationInvalide
from waveaudit.domaine.incident import IDS_REGLES_MINIMAUX

DOSSIER_REGLES = Path(__file__).parents[2] / "donnees" / "regles"


def test_catalogue_reel_charge_les_15_regles_minimales():
    catalogue = CatalogueReglesYaml(DOSSIER_REGLES)
    regles = catalogue.regles()
    assert {r.id for r in regles} == set(IDS_REGLES_MINIMAUX)
    assert regles == sorted(regles, key=lambda r: r.id)


def test_catalogue_reel_verifie_sans_erreur():
    regles = CatalogueReglesYaml(DOSSIER_REGLES).regles()
    assert verifier_regles(regles) == []


def test_verifier_regles_catalogue_vide_signale_les_15_manquantes():
    erreurs = verifier_regles([])
    assert len(erreurs) == len(IDS_REGLES_MINIMAUX)
    for id_minimal in IDS_REGLES_MINIMAUX:
        assert any(id_minimal in erreur for erreur in erreurs)


def test_verifier_regles_identifiant_duplique():
    erreurs = verifier_regles([regle(), regle()])
    assert any("dupliqué" in erreur for erreur in erreurs)


def test_verifier_regles_cle_hors_champs_normalises():
    r = regle(condition={"programme": "sshd", "champs": {"cle_inconnue": "x"}})
    erreurs = verifier_regles([r])
    assert any("cle_inconnue" in erreur for erreur in erreurs)


def test_verifier_regles_cle_agregation_hors_champs_normalises():
    r = regle(agregation={"seuil": 5, "fenetre_s": 300, "par": ["cle_inconnue"]})
    erreurs = verifier_regles([r])
    assert any("cle_inconnue" in erreur for erreur in erreurs)


def test_verifier_regles_programme_non_reconnu():
    r = regle(condition={"programme": "cron", "message_regex": "x"})
    erreurs = verifier_regles([r])
    assert any("cron" in erreur for erreur in erreurs)


def test_verifier_regles_regex_non_compilable():
    r = regle(condition={"programme": "sshd", "champs_regex": {"ip": "[non fermé"}})
    erreurs = verifier_regles([r])
    assert any("regex non compilable" in erreur for erreur in erreurs)


def test_verifier_regles_url_incoherente_avec_id():
    r = regle(
        references=[
            {
                "id": "T1110.001",
                "titre": "Brute Force: Password Guessing",
                "url": "https://attack.mitre.org/techniques/T1110/",
            }
        ]
    )
    erreurs = verifier_regles([r])
    assert any("incohérente" in erreur for erreur in erreurs)


def test_verifier_regles_url_invalide():
    r = regle(
        references=[{"id": "T1110.001", "titre": "x", "url": "https://example.com/T1110/001/"}]
    )
    erreurs = verifier_regles([r])
    assert any("url de référence invalide" in erreur for erreur in erreurs)


@pytest.mark.parametrize("rubrique", ["titre", "description", "impact", "recommandation"])
def test_verifier_regles_jeton_technique_interdit(rubrique):
    r = regle(**{rubrique: "Détection liée à T1110 dans le journal d'audit."})
    erreurs = verifier_regles([r])
    assert any("ATT&CK" in erreur for erreur in erreurs)


def test_verifier_regles_jeton_ipv4_interdit():
    r = regle(description="Adresse 192.0.2.10 observée dans le journal d'audit système.")
    erreurs = verifier_regles([r])
    assert any("IPv4" in erreur for erreur in erreurs)


def test_verifier_regles_jeton_hachage_interdit():
    r = regle(impact="Hachage " + "a1b2c3d4" * 4 + " observé sur le poste concerné.")
    erreurs = verifier_regles([r])
    assert any("hachage" in erreur for erreur in erreurs)


def test_verifier_regles_titre_vide():
    r = regle(titre=" ")
    erreurs = verifier_regles([r])
    assert any("titre vide" in erreur for erreur in erreurs)


def test_verifier_regles_texte_trop_court():
    r = regle(impact="Trop court.")
    erreurs = verifier_regles([r])
    assert any("impact trop court" in erreur for erreur in erreurs)


def test_catalogue_yaml_fichier_invalide_leve_configuration_invalide(tmp_path):
    (tmp_path / "linux.yaml").write_text(
        "- id: INC-LIN-SSH-FORCE-BRUTE\n  titre: x\n", encoding="utf-8"
    )
    with pytest.raises(ConfigurationInvalide):
        CatalogueReglesYaml(tmp_path)


def test_catalogue_yaml_racine_non_liste_leve_configuration_invalide(tmp_path):
    (tmp_path / "linux.yaml").write_text("cle: valeur\n", encoding="utf-8")
    with pytest.raises(ConfigurationInvalide):
        CatalogueReglesYaml(tmp_path)
