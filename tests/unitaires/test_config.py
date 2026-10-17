import re
import shutil
import tomllib
from pathlib import Path

import pytest

from waveaudit.application import config as module_config
from waveaudit.application.config import charger_configuration, racine_projet
from waveaudit.domaine.configuration import Configuration
from waveaudit.domaine.erreurs import ConfigurationInvalide

RACINE = racine_projet()


@pytest.fixture
def fausse_racine(tmp_path, monkeypatch) -> Path:
    """Racine de projet isolée : copie de config/waveaudit.toml, sans fichier local."""
    (tmp_path / "config").mkdir()
    shutil.copy(RACINE / "config" / "waveaudit.toml", tmp_path / "config" / "waveaudit.toml")
    monkeypatch.setattr(module_config, "racine_projet", lambda: tmp_path)
    return tmp_path


def test_racine_projet():
    assert (RACINE / "config" / "waveaudit.toml").is_file()
    assert (RACINE / "pyproject.toml").is_file()


def test_defauts_du_toml_egaux_au_modele():
    with (RACINE / "config" / "waveaudit.toml").open("rb") as fichier:
        donnees = tomllib.load(fichier)
    assert Configuration.model_validate(donnees) == Configuration()


def test_defauts(fausse_racine):
    config = charger_configuration()
    assert config.moteur.mode == "local-gere"
    assert config.moteur.timeout_s == 180.0
    assert config.moteur.seed == 42
    assert config.moteur.taille_max_note == 6000
    assert config.reseau.hotes_autorises == ["127.0.0.1", "::1", "localhost"]
    assert config.recherche.k1 == 1.5 and config.recherche.b == 0.75
    assert config.ui.hote == "127.0.0.1" and config.ui.port == 8765


def test_chemins_relatifs_a_la_racine(fausse_racine, tmp_path, monkeypatch):
    autre = tmp_path / "ailleurs"
    autre.mkdir()
    monkeypatch.chdir(autre)
    config = charger_configuration()
    assert config.chemins.var == fausse_racine / "var"
    assert config.chemins.catalogue == fausse_racine / "donnees" / "catalogue"
    assert config.chemins.theme_prive == fausse_racine / "theme-prive"
    assert config.chemins.manifeste == fausse_racine / "config" / "artefacts.toml"


def test_surcharge_locale_puis_fichier(fausse_racine, tmp_path):
    (fausse_racine / "waveaudit.local.toml").write_text(
        '[moteur]\nmode = "externe"\nbase_url = "http://127.0.0.1:9/v1"\nseed = 7\n',
        encoding="utf-8",
    )
    supplement = tmp_path / "supplement.toml"
    absolu = (tmp_path / "var-test").as_posix()
    supplement.write_text(f'[moteur]\nseed = 8\n[chemins]\nvar = "{absolu}"\n', encoding="utf-8")
    config = charger_configuration(supplement)
    assert config.moteur.mode == "externe"
    assert config.moteur.base_url == "http://127.0.0.1:9/v1"
    assert config.moteur.seed == 8
    assert config.moteur.temperature == 0.2  # fusion profonde : le reste de [moteur] demeure
    assert config.chemins.var == tmp_path / "var-test"
    assert config.chemins.catalogue == fausse_racine / "donnees" / "catalogue"


@pytest.mark.parametrize(
    "contenu",
    [
        "[moteur]\ninconnue = 1\n",
        "[section_inconnue]\na = 1\n",
        '[moteur]\nmode = "cloud"\n',
        '[moteur]\ntimeout_s = "long"\n',
        "[moteur\n",
    ],
)
def test_configuration_invalide(fausse_racine, tmp_path, contenu):
    fichier = tmp_path / "mauvais.toml"
    fichier.write_text(contenu, encoding="utf-8")
    with pytest.raises(ConfigurationInvalide):
        charger_configuration(fichier)


def test_fichier_absent(fausse_racine, tmp_path):
    with pytest.raises(ConfigurationInvalide):
        charger_configuration(tmp_path / "absent.toml")


def test_waveaudit_toml_cles_exactes():
    with (RACINE / "config" / "waveaudit.toml").open("rb") as fichier:
        donnees = tomllib.load(fichier)
    assert {s: list(v) for s, v in donnees.items()} == {
        s: list(type(v).model_fields) for s, v in Configuration()
    }


CHAMPS_ARTEFACT = [
    "nom",
    "role",
    "version",
    "url",
    "sha256",
    "taille",
    "licence",
    "source",
    "destination",
    "extraire",
    "executable",
    "prefixe_systeme",
]
CHAMPS_FACULTATIFS = ["mode_json", "reflexion"]


def test_manifeste_artefacts():
    with (RACINE / "config" / "artefacts.toml").open("rb") as fichier:
        artefacts = tomllib.load(fichier)["artefact"]
    assert [a["nom"] for a in artefacts] == [
        "llama-server-b11714",
        "granite-4.0-1b-q4km",
        "minicpm5-1b-q4km",
        "qwen3-1.7b-q4km",
        "qwen3.5-0.8b-q4km",
    ]
    assert [a["role"] for a in artefacts] == [
        "moteur",
        "modele_defaut",
        "modele_repli",
        "candidat",
        "candidat",
    ]
    for artefact in artefacts:
        assert list(artefact)[: len(CHAMPS_ARTEFACT)] == CHAMPS_ARTEFACT
        assert set(list(artefact)[len(CHAMPS_ARTEFACT) :]) <= set(CHAMPS_FACULTATIFS)
        assert re.fullmatch(r"[0-9a-f]{64}", artefact["sha256"])
        assert isinstance(artefact["taille"], int) and artefact["taille"] > 0
        assert artefact["url"].startswith("https://")
        if artefact["role"] == "moteur":
            assert artefact["extraire"] is True
            assert artefact["executable"] == "llama-server.exe"
        else:
            assert artefact["extraire"] is False and artefact["executable"] == ""
            assert artefact["destination"] == "modeles/" + artefact["url"].rsplit("/", 1)[1]
    prefixes = {a["nom"]: a["prefixe_systeme"] for a in artefacts}
    assert prefixes["qwen3-1.7b-q4km"] == "/no_think"
    assert sum(1 for p in prefixes.values() if p) == 1
    # V1 : réflexion coupée pour les deux modèles qui laissaient `content` vide ; mode_json absent.
    assert {a["nom"]: a["reflexion"] for a in artefacts if "reflexion" in a} == {
        "minicpm5-1b-q4km": False,
        "qwen3.5-0.8b-q4km": False,
    }
    assert not any("mode_json" in a for a in artefacts)


def test_chemin_relatif_resolu_contre_la_racine(fausse_racine, tmp_path, monkeypatch):
    (fausse_racine / "surcharge.toml").write_text("[moteur]\nseed = 9\n", encoding="utf-8")
    autre = tmp_path / "ailleurs"
    autre.mkdir()
    (autre / "surcharge.toml").write_text("[moteur]\nseed = 1\n", encoding="utf-8")
    monkeypatch.chdir(autre)
    assert charger_configuration(Path("surcharge.toml")).moteur.seed == 9


def test_section_incident_et_chemin_regles(fausse_racine):
    config = charger_configuration()
    assert config.chemins.regles == fausse_racine / "donnees" / "regles"
    assert config.incident.decalage_syslog == "+02:00"
    assert config.incident.max_preuves == 10
    assert config.incident.longueur_max_recit == 800
    assert config.incident.max_tokens == 1000


@pytest.mark.parametrize(
    "contenu",
    [
        '[incident]\ndecalage_syslog = "+2:00"\n',
        '[incident]\ndecalage_syslog = "Europe/Paris"\n',
        "[incident]\nmax_preuves = 0\n",
        "[incident]\nlongueur_max_recit = 99\n",
        "[incident]\nmax_tokens = 99\n",
        "[incident]\ninconnue = 1\n",
    ],
)
def test_section_incident_invalide(fausse_racine, tmp_path, contenu):
    fichier = tmp_path / "mauvais.toml"
    fichier.write_text(contenu, encoding="utf-8")
    with pytest.raises(ConfigurationInvalide):
        charger_configuration(fichier)


def test_section_incident_surchargee(fausse_racine, tmp_path):
    fichier = tmp_path / "incident.toml"
    fichier.write_text('[incident]\ndecalage_syslog = "-05:30"\n', encoding="utf-8")
    config = charger_configuration(fichier)
    assert config.incident.decalage_syslog == "-05:30"
    assert config.incident.max_preuves == 10
