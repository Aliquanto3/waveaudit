"""Tests de `installation/` : manifeste, téléchargement vérifié, extraction, SBOM
(contrats §11, AD-12, CAP-10, CAP-11)."""

import io
import re
import zipfile
from collections import Counter
from pathlib import Path

import httpx
import pytest

from waveaudit.domaine.erreurs import ConfigurationInvalide, EmpreinteInvalide
from waveaudit.installation import manifeste, sbom, telechargement
from waveaudit.installation.manifeste import Artefact

RACINE = Path(__file__).resolve().parents[2]
MANIFESTE_DEPOT = RACINE / "config" / "artefacts.toml"


def _artefact(**surcharges) -> Artefact:
    defauts = dict(
        nom="truc",
        role="modele_defaut",
        version="1",
        url="https://exemple.invalid/truc.bin",
        sha256="",
        taille=0,
        licence="MIT",
        source="https://exemple.invalid",
        destination="modeles/truc.bin",
        extraire=False,
        executable="",
        prefixe_systeme="",
    )
    defauts.update(surcharges)
    return Artefact.model_validate(defauts)


def _contenu(donnees: bytes) -> dict[str, str]:
    return {"sha256": __import__("hashlib").sha256(donnees).hexdigest(), "taille": len(donnees)}


# --- manifeste ---------------------------------------------------------------


def test_manifeste_du_depot_cinq_artefacts_roles_uniques_sauf_candidat():
    artefacts = manifeste.charger(MANIFESTE_DEPOT)
    assert len(artefacts) == 5
    roles = Counter(artefact.role for artefact in artefacts)
    for role, nombre in roles.items():
        if role != "candidat":
            assert nombre == 1, f"rôle {role} devrait être unique"
    assert roles["candidat"] == 2


def test_manifeste_du_depot_urls_epinglees_sur_un_commit_ou_un_tag():
    for artefact in manifeste.charger(MANIFESTE_DEPOT):
        assert "/resolve/main/" not in artefact.url
        assert "/download/latest/" not in artefact.url
        if "huggingface.co" in artefact.url:
            segment = artefact.url.split("/resolve/")[1].split("/")[0]
            assert re.fullmatch(r"[0-9a-f]{40}", segment), artefact.url
        elif "github.com" in artefact.url:
            segment = artefact.url.split("/download/")[1].split("/")[0]
            assert segment not in {"latest", "main"}, artefact.url
        else:
            pytest.fail(f"URL inattendue : {artefact.url}")


def test_charger_manifeste_absent_leve_configuration_invalide(tmp_path):
    with pytest.raises(ConfigurationInvalide):
        manifeste.charger(tmp_path / "absent.toml")


def test_charger_manifeste_vide_leve_configuration_invalide(tmp_path):
    chemin_toml = tmp_path / "artefacts.toml"
    chemin_toml.write_text("", encoding="utf-8")
    with pytest.raises(ConfigurationInvalide):
        manifeste.charger(chemin_toml)


def test_par_role_leve_si_non_unique():
    artefacts = [_artefact(nom="a", role="candidat"), _artefact(nom="b", role="candidat")]
    with pytest.raises(ConfigurationInvalide):
        manifeste.par_role(artefacts, "candidat")


def test_par_role_leve_si_absent():
    with pytest.raises(ConfigurationInvalide):
        manifeste.par_role([_artefact()], "moteur")


def test_par_nom_leve_si_inconnu():
    with pytest.raises(ConfigurationInvalide):
        manifeste.par_nom([_artefact(nom="a")], "inconnu")


def test_chemin_moteur_sans_executable_leve():
    artefact = _artefact(role="moteur", executable="")
    with pytest.raises(ConfigurationInvalide):
        manifeste.chemin(artefact, Path("var"))


def test_chemin_moteur_resout_executable(tmp_path):
    artefact = _artefact(role="moteur", destination="moteur/b1", executable="llama-server.exe")
    assert manifeste.chemin(artefact, tmp_path) == tmp_path / "moteur" / "b1" / "llama-server.exe"


# --- téléchargement ------------------------------------------------------------


def test_telechargement_ok_renomme_depuis_part(tmp_path):
    contenu = b"contenu de l'artefact"
    artefact = _artefact(**_contenu(contenu))

    def repondeur(requete: httpx.Request) -> httpx.Response:
        assert requete.url == httpx.URL(artefact.url)
        return httpx.Response(200, content=contenu)

    transport = httpx.MockTransport(repondeur)
    resultat = telechargement.telecharger(artefact, tmp_path, transport=transport)

    assert resultat == tmp_path / artefact.destination
    assert resultat.read_bytes() == contenu
    assert not resultat.with_name(resultat.name + ".part").exists()


def test_mauvaise_empreinte_leve_et_supprime_le_fichier(tmp_path):
    artefact = _artefact(sha256="0" * 64, taille=999)

    def repondeur(requete: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"autre contenu")

    transport = httpx.MockTransport(repondeur)
    with pytest.raises(EmpreinteInvalide):
        telechargement.telecharger(artefact, tmp_path, transport=transport)

    assert not (tmp_path / artefact.destination).exists()


def test_fichier_deja_valide_est_saute_sans_requete(tmp_path):
    contenu = b"deja la et correct"
    artefact = _artefact(**_contenu(contenu))
    cible = tmp_path / artefact.destination
    cible.parent.mkdir(parents=True)
    cible.write_bytes(contenu)

    def repondeur(requete: httpx.Request) -> httpx.Response:
        raise AssertionError("aucune requête ne devrait partir : fichier déjà valide")

    transport = httpx.MockTransport(repondeur)
    resultat = telechargement.telecharger(artefact, tmp_path, transport=transport)

    assert resultat == cible
    assert resultat.read_bytes() == contenu


def test_fichier_corrompu_preexistant_est_retelecharge(tmp_path):
    contenu = b"bon contenu"
    artefact = _artefact(**_contenu(contenu))
    cible = tmp_path / artefact.destination
    cible.parent.mkdir(parents=True)
    cible.write_bytes(b"mauvais contenu present avant")

    appels = []

    def repondeur(requete: httpx.Request) -> httpx.Response:
        appels.append(requete)
        return httpx.Response(200, content=contenu)

    transport = httpx.MockTransport(repondeur)
    resultat = telechargement.telecharger(artefact, tmp_path, transport=transport)

    assert len(appels) == 1
    assert resultat.read_bytes() == contenu


def test_extraction_zip_et_executable_resolu(tmp_path):
    contenu_exe = b"faux binaire"
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w") as archive:
        archive.writestr("llama-server.exe", contenu_exe)
    donnees_zip = tampon.getvalue()

    artefact = _artefact(
        nom="llama-server-test",
        role="moteur",
        destination="moteur/b1",
        extraire=True,
        executable="llama-server.exe",
        **_contenu(donnees_zip),
    )

    def repondeur(requete: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=donnees_zip)

    transport = httpx.MockTransport(repondeur)
    resultat = telechargement.telecharger(artefact, tmp_path, transport=transport)

    assert resultat == tmp_path / "moteur" / "b1" / "llama-server.exe"
    assert resultat.read_bytes() == contenu_exe


def test_installer_telecharge_moteur_defaut_repli_sans_candidats(tmp_path, monkeypatch):
    moteur = _artefact(nom="moteur", role="moteur", executable="x.exe")
    defaut = _artefact(nom="defaut", role="modele_defaut")
    repli = _artefact(nom="repli", role="modele_repli")
    candidat = _artefact(nom="candidat", role="candidat")
    manifeste_complet = [moteur, defaut, repli, candidat]

    appeles: list[str] = []
    monkeypatch.setattr(
        telechargement,
        "telecharger",
        lambda artefact, var, transport=None: appeles.append(artefact.nom) or var / artefact.nom,
    )

    resultats = telechargement.installer(manifeste_complet, tmp_path, False)

    assert appeles == ["moteur", "defaut", "repli"]
    assert len(resultats) == 3


def test_installer_avec_candidats_ajoute_les_candidats(tmp_path, monkeypatch):
    moteur = _artefact(nom="moteur", role="moteur", executable="x.exe")
    defaut = _artefact(nom="defaut", role="modele_defaut")
    repli = _artefact(nom="repli", role="modele_repli")
    candidat1 = _artefact(nom="candidat1", role="candidat")
    candidat2 = _artefact(nom="candidat2", role="candidat")
    manifeste_complet = [moteur, defaut, repli, candidat1, candidat2]

    appeles: list[str] = []
    monkeypatch.setattr(
        telechargement,
        "telecharger",
        lambda artefact, var, transport=None: appeles.append(artefact.nom) or var / artefact.nom,
    )

    telechargement.installer(manifeste_complet, tmp_path, True)

    assert appeles == ["moteur", "defaut", "repli", "candidat1", "candidat2"]


# --- sbom -----------------------------------------------------------------


def test_sbom_appelle_la_bonne_commande(tmp_path, monkeypatch):
    appels = []

    def faux_run(commande, check):
        appels.append((commande, check))

        class Resultat:
            returncode = 0

        return Resultat()

    monkeypatch.setattr(sbom.subprocess, "run", faux_run)

    cible = sbom.generer(tmp_path)

    assert cible == tmp_path / "sbom.cdx.json"
    assert len(appels) == 1
    commande, verifie = appels[0]
    assert verifie is True
    assert commande[1:4] == ["-m", "cyclonedx_py", "environment"]
    assert "--output-file" in commande
    assert str(cible) in commande
