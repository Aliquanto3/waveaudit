"""Tests de l'adaptateur catalogue (CAP-2, contrats §15, §16)."""

from pathlib import Path

import pytest
import yaml

from waveaudit.adaptateurs.catalogue_yaml import IDENTIFIANTS_FIGES, CatalogueYaml, verifier
from waveaudit.application.config import racine_projet
from waveaudit.domaine.erreurs import ConfigurationInvalide, EntreeInvalide

CONSTAT_MINIMAL = {
    "id": "WEB-TEST",
    "titre": "Constat de test",
    "famille": "web",
    "mots_cles": ["un", "deux", "trois", "four", "five", "six"],
    "description": "d",
    "impact": "i",
    "recommandation": "r",
    "cvss_vecteur": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
    "references": [
        {"id": "CWE-79", "titre": "XSS", "url": "https://cwe.mitre.org/data/definitions/79.html"}
    ],
    "source": "Rédaction WaveAudit d'après CWE-79, licence du dépôt",
}


def _ecrire(dossier: Path, nom: str, constats: list[dict]) -> None:
    (dossier / nom).write_text(yaml.safe_dump(constats, allow_unicode=True), encoding="utf-8")


def _constat(**overrides) -> dict:
    constat = {**CONSTAT_MINIMAL}
    constat.update(overrides)
    return constat


def _catalogue_complet(dossier: Path) -> None:
    """Un catalogue minimal mais complet : les 35 identifiants figés, en familles correctes."""
    par_famille: dict[str, list[dict]] = {}
    for identifiant in IDENTIFIANTS_FIGES:
        famille = identifiant.split("-", 1)[0].lower()
        par_famille.setdefault(famille, []).append(
            _constat(id=identifiant, famille=famille, titre=identifiant)
        )
    for famille, constats in par_famille.items():
        _ecrire(dossier, f"{famille}.yaml", constats)


def test_catalogue_du_depot_est_valide():
    erreurs = verifier(racine_projet() / "donnees" / "catalogue")
    assert erreurs == []


def test_catalogue_du_depot_charge_au_moins_35_constats():
    constats = CatalogueYaml(racine_projet() / "donnees" / "catalogue").constats()
    assert len(constats) >= 35
    assert len({c.id for c in constats}) == len(constats)
    assert [c.id for c in constats] == sorted(c.id for c in constats)


def test_obtenir_renvoie_le_constat_demande():
    catalogue = CatalogueYaml(racine_projet() / "donnees" / "catalogue")
    assert catalogue.obtenir("WEB-XSS-REFLECHI").id == "WEB-XSS-REFLECHI"


def test_obtenir_leve_entree_invalide_si_absent():
    catalogue = CatalogueYaml(racine_projet() / "donnees" / "catalogue")
    with pytest.raises(EntreeInvalide):
        catalogue.obtenir("INCONNU")


def test_constats_leve_configuration_invalide_si_id_duplique(tmp_path: Path):
    _ecrire(tmp_path, "web.yaml", [_constat(), _constat()])
    with pytest.raises(ConfigurationInvalide):
        CatalogueYaml(tmp_path).constats()


def test_catalogue_minimal_complet_est_valide(tmp_path: Path):
    _catalogue_complet(tmp_path)
    assert verifier(tmp_path) == []


def test_verifier_detecte_schema_invalide(tmp_path: Path):
    _ecrire(tmp_path, "web.yaml", [{**CONSTAT_MINIMAL, "champ_inconnu": "x"}])
    erreurs = verifier(tmp_path)
    assert any("web.yaml" in e for e in erreurs)


def test_verifier_detecte_doublon_id(tmp_path: Path):
    _ecrire(tmp_path, "web.yaml", [_constat(), _constat()])
    erreurs = verifier(tmp_path)
    assert any("dupliqué" in e for e in erreurs)


def test_verifier_detecte_prefixe_incoherent_avec_le_fichier(tmp_path: Path):
    _ecrire(tmp_path, "ad.yaml", [_constat(id="WEB-TEST", famille="web")])
    erreurs = verifier(tmp_path)
    assert any("ad.yaml" in e and "préfixe" in e for e in erreurs)


def test_verifier_detecte_vecteur_cvss_non_evaluable(tmp_path: Path):
    vecteur = "CVSS:3.1/AV:X/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
    _ecrire(tmp_path, "web.yaml", [_constat(cvss_vecteur=vecteur)])
    erreurs = verifier(tmp_path)
    assert any("web.yaml" in e for e in erreurs)


def test_verifier_detecte_vecteur_cvss_non_canonique(tmp_path: Path):
    # Métriques dans un ordre différent de AV/AC/PR/UI/S/C/I/A : pas canonique.
    vecteur = "CVSS:3.1/AC:L/AV:N/PR:N/UI:N/S:U/C:H/I:H/A:H"
    _ecrire(tmp_path, "web.yaml", [_constat(cvss_vecteur=vecteur)])
    erreurs = verifier(tmp_path)
    assert any("non canonique" in e for e in erreurs)


def test_verifier_detecte_reference_de_forme_non_canonique(tmp_path: Path):
    _ecrire(
        tmp_path,
        "web.yaml",
        [_constat(references=[{"id": "PAS-CANONIQUE", "titre": "x", "url": "https://x.test/"}])],
    )
    erreurs = verifier(tmp_path)
    assert any("forme non canonique" in e for e in erreurs)


def test_verifier_detecte_url_de_reference_non_https(tmp_path: Path):
    _ecrire(
        tmp_path,
        "web.yaml",
        [_constat(references=[{"id": "CWE-79", "titre": "x", "url": "http://cwe.mitre.org/x"}])],
    )
    erreurs = verifier(tmp_path)
    assert any("non https" in e for e in erreurs)


def test_verifier_detecte_identifiant_fige_manquant(tmp_path: Path):
    _ecrire(tmp_path, "web.yaml", [_constat()])
    erreurs = verifier(tmp_path)
    assert any("identifiant figé manquant" in e for e in erreurs)


def test_verifier_detecte_total_insuffisant(tmp_path: Path):
    _catalogue_complet(tmp_path)
    # On retire un constat du fichier web pour retomber sous le minimum attendu n'est pas
    # trivial sans casser les identifiants figés : on construit un catalogue volontairement
    # réduit, sans viser la complétude des 35 figés, pour isoler la règle du total.
    _ecrire(tmp_path, "web.yaml", [_constat()])
    for fichier in ("ad.yaml", "infra.yaml", "config.yaml", "crypto.yaml", "autre.yaml"):
        (tmp_path / fichier).unlink(missing_ok=True)
    erreurs = verifier(tmp_path)
    assert any("au moins 30 attendus" in e for e in erreurs)


def test_charger_leve_configuration_invalide_si_yaml_illisible(tmp_path: Path):
    (tmp_path / "web.yaml").write_text(": : :", encoding="utf-8")
    with pytest.raises(ConfigurationInvalide):
        CatalogueYaml(tmp_path).constats()


def test_charger_leve_configuration_invalide_si_racine_pas_une_liste(tmp_path: Path):
    (tmp_path / "web.yaml").write_text("cle: valeur", encoding="utf-8")
    with pytest.raises(ConfigurationInvalide):
        CatalogueYaml(tmp_path).constats()


def test_charger_leve_configuration_invalide_si_entree_invalide(tmp_path: Path):
    _ecrire(tmp_path, "web.yaml", [{**CONSTAT_MINIMAL, "famille": "inconnue"}])
    with pytest.raises(ConfigurationInvalide):
        CatalogueYaml(tmp_path).constats()


def test_verifier_sur_yaml_illisible_renvoie_une_erreur_sans_lever(tmp_path: Path):
    (tmp_path / "web.yaml").write_text(": : :", encoding="utf-8")
    erreurs = verifier(tmp_path)
    assert any("web.yaml" in e for e in erreurs)
