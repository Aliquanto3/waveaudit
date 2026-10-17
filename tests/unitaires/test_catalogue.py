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


# --- Revue story 4 ---------------------------------------------------------------------------

DOMAINES_REFERENCES = ("cwe.mitre.org", "owasp.org", "cyber.gouv.fr", "ssi.gouv.fr")


def test_contenu_du_catalogue_du_depot_suit_le_cahier_des_charges():
    """Règles de la story hors `verifier` (§15) : 6-12 mots-clés, source, URL publiques."""
    for c in CatalogueYaml(racine_projet() / "donnees" / "catalogue").constats():
        assert 6 <= len(c.mots_cles) <= 12, c.id
        # Garde-fou §6 : un titre de fiche de moins de 20 caractères est remplacé (a_revoir).
        assert len(c.titre) >= 20, c.id
        assert c.source.startswith("Rédaction WaveAudit d'après "), c.id
        assert c.source.endswith(", licence du dépôt"), c.id
        for ref in c.references:
            assert ref.url.split("/")[2].removeprefix("www.") in DOMAINES_REFERENCES, c.id
            assert ref.id in c.source, (c.id, ref.id)
            if ref.id.startswith("CWE-"):
                numero = ref.id.removeprefix("CWE-")
                assert ref.url == f"https://cwe.mitre.org/data/definitions/{numero}.html", c.id
            if ref.id[0] == "A" and ":" in ref.id:
                rang, annee = ref.id.split(":")
                assert f"/Top10/{rang}_{annee}-" in ref.url, c.id


def test_constats_leve_configuration_invalide_si_dossier_absent(tmp_path: Path):
    absent = tmp_path / "absent"
    with pytest.raises(ConfigurationInvalide, match="introuvable"):
        CatalogueYaml(absent).constats()
    assert verifier(absent) == [f"catalogue: dossier introuvable ({absent})"]


def test_erreurs_de_verifier_tiennent_sur_une_ligne(tmp_path: Path):
    _ecrire(tmp_path, "web.yaml", [{"id": "WEB-X", "titre": "t"}])
    (tmp_path / "ad.yaml").write_text("- id: [\n  x: : :\n", encoding="utf-8")
    erreurs = verifier(tmp_path)
    assert any(e.startswith("web.yaml:WEB-X: ") for e in erreurs)
    assert any(e.startswith("ad.yaml: YAML illisible") for e in erreurs)
    assert all("\n" not in e for e in erreurs)


def test_obtenir_ne_relit_pas_le_catalogue(tmp_path: Path):
    _ecrire(tmp_path, "web.yaml", [_constat()])
    catalogue = CatalogueYaml(tmp_path)
    assert catalogue.obtenir("WEB-TEST").id == "WEB-TEST"
    (tmp_path / "web.yaml").unlink()
    assert catalogue.obtenir("WEB-TEST").id == "WEB-TEST"
    assert [c.id for c in catalogue.constats()] == ["WEB-TEST"]
