"""Composition (contrats §9, AD-11) : choix du modèle par RAM, modes externe et local-gere."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from waveaudit.adaptateurs import memoire_psutil
from waveaudit.application import composition
from waveaudit.domaine.erreurs import ConfigurationInvalide
from waveaudit.installation import manifeste

GO = composition.OCTETS_PAR_GO


@pytest.fixture
def artefacts(config_test):
    return manifeste.charger(config_test.chemins.manifeste)


def _local(config, **moteur):
    return config.model_copy(
        update={"moteur": config.moteur.model_copy(update={"mode": "local-gere", **moteur})}
    )


@pytest.mark.parametrize(("ram_go", "role"), [(2.0, "modele_repli"), (16.0, "modele_defaut")])
def test_choix_par_ram(config_test, artefacts, monkeypatch, ram_go, role):
    monkeypatch.setattr(memoire_psutil, "ram_disponible_octets", lambda: int(ram_go * GO))
    choisi = composition.choisir_modele(_local(config_test), artefacts, None)
    assert choisi.role == role


def test_choix_explicite_et_erreurs(config_test, artefacts, monkeypatch):
    monkeypatch.setattr(memoire_psutil, "ram_disponible_octets", lambda: 0)
    config = _local(config_test, modele="qwen3-1.7b-q4km")
    assert composition.choisir_modele(config, artefacts, None).nom == "qwen3-1.7b-q4km"
    assert composition.choisir_modele(config, artefacts, "granite-4.0-1b-q4km").role == (
        "modele_defaut"
    )
    with pytest.raises(ConfigurationInvalide):
        composition.choisir_modele(config, artefacts, "inconnu")
    with pytest.raises(ConfigurationInvalide):
        composition.choisir_modele(config, artefacts, "llama-server-b11714")


def test_externe_sans_processus(config_test):
    config = config_test.model_copy(
        update={"moteur": config_test.moteur.model_copy(update={"prefixe_systeme": "P"})}
    )
    with composition.ouvrir(config, "mon-modele") as (ports, info):
        ports.moteur.sonder()
        assert info.pid is None
        assert info.nom_modele == "mon-modele"
        assert info.base_url == config.moteur.base_url
        assert ports.prefixe_systeme == "P"


def test_externe_base_url_vide(config_test):
    config = config_test.model_copy(
        update={"moteur": config_test.moteur.model_copy(update={"base_url": ""})}
    )
    with pytest.raises(ConfigurationInvalide):
        with composition.ouvrir(config, None):
            pass


class _FauxServeur:
    instances: list["_FauxServeur"] = []

    def __init__(self, binaire, gguf, ctx, threads, delai_s, journal):
        self.args = (binaire, gguf, ctx, threads, delai_s, journal)
        self.base_url = "http://127.0.0.1:9/v1"
        self.pid = 4242
        self.ouvert = False
        _FauxServeur.instances.append(self)

    def __enter__(self):
        self.ouvert = True
        return self

    def __exit__(self, *exc):
        self.ouvert = False


def _installer(config, artefacts, *noms):
    var = config.chemins.var
    for nom in noms:
        fichier = manifeste.chemin(manifeste.par_nom(artefacts, nom), var)
        fichier.parent.mkdir(parents=True, exist_ok=True)
        fichier.write_bytes(b"x")


def test_local_gere_demarre_llama_server(config_test, artefacts, monkeypatch):
    monkeypatch.setattr(composition, "LlamaServer", _FauxServeur)
    monkeypatch.setattr(memoire_psutil, "ram_disponible_octets", lambda: 2 * GO)
    _FauxServeur.instances.clear()
    config = _local(config_test, ctx=1024, threads=3, delai_demarrage_s=7.0)
    _installer(config, artefacts, "llama-server-b11714", "minicpm5-1b-q4km")
    with composition.ouvrir(config, None, id_lot="20261017-120000") as (ports, info):
        serveur = _FauxServeur.instances[0]
        assert serveur.ouvert
        assert info.pid == 4242
        assert info.nom_modele == "minicpm5-1b-q4km"
        assert info.base_url == serveur.base_url
        assert ports.moteur._modele_api == "minicpm5-1b-q4km"
    binaire, gguf, ctx, threads, delai_s, journal = serveur.args
    var = config.chemins.var
    assert binaire == var / "moteur" / "b11714" / "llama-server.exe"
    assert gguf == var / "modeles" / "MiniCPM5-1B-Q4_K_M.gguf"
    assert (ctx, threads, delai_s) == (1024, 3, 7.0)
    assert journal == var / "journaux" / "llama-server-20261017-120000.log"
    assert not serveur.ouvert


def test_local_gere_artefacts_absents(config_test, monkeypatch):
    monkeypatch.setattr(composition, "LlamaServer", _FauxServeur)
    _FauxServeur.instances.clear()
    with pytest.raises(ConfigurationInvalide, match="installer"):
        with composition.ouvrir(_local(config_test, modele="granite-4.0-1b-q4km"), None):
            pass
    assert _FauxServeur.instances == []


def test_mesure_memoire():
    mesure = composition.creer_mesure_memoire()
    assert mesure.rss_octets(os.getpid()) > 0
    fini = subprocess.Popen([sys.executable, "-c", "pass"])
    fini.wait()
    assert mesure.rss_octets(fini.pid) is None


def test_chemins_sous_tmp(config_test, tmp_path):
    assert Path(config_test.chemins.var).is_relative_to(tmp_path)


# --- ouvrir_moteur_incident (CERT, contrats §21) ---------------------------------------------


def test_ouvrir_moteur_incident_externe(config_test):
    config = config_test.model_copy(
        update={"moteur": config_test.moteur.model_copy(update={"prefixe_systeme": "P"})}
    )
    with composition.ouvrir_moteur_incident(config, "mon-modele") as (moteur, prefixe, info):
        moteur.sonder()
        assert prefixe == "P"
        assert info.pid is None
        assert info.nom_modele == "mon-modele"
        assert info.base_url == config.moteur.base_url
    with composition.ouvrir_moteur_incident(config, None) as (_, _, info):
        assert info.nom_modele == "externe"


def test_ouvrir_moteur_incident_sans_port_des_fiches(config_test, monkeypatch):
    """Ni exporteur Word ni catalogue des fiches : le CERT n'ouvre que le moteur."""

    def interdit(*args, **kwargs):
        raise AssertionError("port des fiches instancié")

    monkeypatch.setattr(composition, "ExportDocx", interdit)
    monkeypatch.setattr(composition, "CatalogueYaml", interdit)
    with composition.ouvrir_moteur_incident(config_test, None) as (moteur, _, _):
        moteur.sonder()


def test_ouvrir_moteur_incident_base_url_vide(config_test):
    config = config_test.model_copy(
        update={"moteur": config_test.moteur.model_copy(update={"base_url": ""})}
    )
    with pytest.raises(ConfigurationInvalide):
        with composition.ouvrir_moteur_incident(config, None):
            pass


def test_ouvrir_moteur_incident_local_gere(config_test, artefacts, monkeypatch):
    monkeypatch.setattr(composition, "LlamaServer", _FauxServeur)
    _FauxServeur.instances.clear()
    config = _local(config_test)
    _installer(config, artefacts, "llama-server-b11714", "granite-4.0-1b-q4km")
    with composition.ouvrir_moteur_incident(
        config, "granite-4.0-1b-q4km", id_lot="20261017-130000"
    ) as (moteur, prefixe, info):
        (serveur,) = _FauxServeur.instances
        assert serveur.ouvert
        assert info.pid == 4242 and info.nom_modele == "granite-4.0-1b-q4km"
        assert moteur._modele_api == "granite-4.0-1b-q4km"
        assert prefixe == manifeste.par_nom(artefacts, "granite-4.0-1b-q4km").prefixe_systeme
        assert serveur.args[-1].name == "llama-server-20261017-130000.log"
    assert not serveur.ouvert
