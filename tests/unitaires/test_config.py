import re
import shutil
import tomllib
from pathlib import Path

import pytest
from pydantic import ValidationError

from waveaudit.application import config as module_config
from waveaudit.application.config import charger_configuration, racine_projet
from waveaudit.domaine.configuration import Configuration
from waveaudit.domaine.erreurs import ConfigurationInvalide
from waveaudit.installation import manifeste

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
CHAMPS_FACULTATIFS = ["mode_json", "reflexion", "repeat_penalty", "duree_indicative_s"]
ARTEFACT_MINIMAL = {
    "nom": "m",
    "role": "candidat",
    "version": "1",
    "url": "https://exemple.invalid/m.gguf",
    "sha256": "0" * 64,
    "taille": 1,
    "licence": "MIT",
    "source": "https://exemple.invalid",
    "destination": "modeles/m.gguf",
    "extraire": False,
    "executable": "",
    "prefixe_systeme": "",
}


def test_manifeste_artefacts():
    with (RACINE / "config" / "artefacts.toml").open("rb") as fichier:
        artefacts = tomllib.load(fichier)["artefact"]
    # v2 (CAP-7) : ordre moteur, défaut, repli, candidats ; qwen3.5 repli, MiniCPM5 candidat.
    # Q5 : granite reste défaut (CAP-6 non tenu par qwen3-1.7b, arbitrage du 2026-10-18,
    # bilan-modeles.md section v2) ; qwen3-1.7b redevient candidat.
    assert [a["nom"] for a in artefacts] == [
        "llama-server-b11714",
        "granite-4.0-1b-q4km",
        "qwen3.5-0.8b-q4km",
        "minicpm5-1b-q4km",
        "qwen3-1.7b-q4km",
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
    # Q5 (CAP-6) : pénalité de répétition mesurée au rebanc pour les deux modèles mesurés
    # seulement ; durée indicative pour chaque modèle (médiane du rebanc pour ces deux-là).
    assert {a["nom"]: a["repeat_penalty"] for a in artefacts if "repeat_penalty" in a} == {
        "qwen3-1.7b-q4km": 1.1,
        "granite-4.0-1b-q4km": 1.1,
    }
    assert {a["nom"]: a.get("duree_indicative_s") for a in artefacts if a["role"] != "moteur"} == {
        "qwen3-1.7b-q4km": 36.2,
        "qwen3.5-0.8b-q4km": 11.4,
        "minicpm5-1b-q4km": 12.9,
        "granite-4.0-1b-q4km": 27.9,
    }
    # Le manifeste se charge avec le modèle `Artefact` (extra="forbid").
    noms = [a.nom for a in manifeste.charger(RACINE / "config" / "artefacts.toml")]
    assert noms == [a["nom"] for a in artefacts]


@pytest.mark.parametrize("valeur", [0.0, -0.1, 2.01])
def test_manifeste_repeat_penalty_borne(valeur):
    with pytest.raises(ValidationError):
        manifeste.Artefact.model_validate({**ARTEFACT_MINIMAL, "repeat_penalty": valeur})


def test_manifeste_champs_facultatifs_v2():
    artefact = manifeste.Artefact.model_validate(
        {**ARTEFACT_MINIMAL, "repeat_penalty": 1.1, "duree_indicative_s": 12.5}
    )
    assert artefact.repeat_penalty == 1.1 and artefact.duree_indicative_s == 12.5
    defaut = manifeste.Artefact.model_validate(ARTEFACT_MINIMAL)
    assert defaut.repeat_penalty is None and defaut.duree_indicative_s is None


def test_defauts_v2(fausse_racine):
    config = charger_configuration()
    assert config.moteur.repeat_penalty == 0.0
    assert config.fiches.langue == "fr"
    assert config.ui.inactivite_moteur_s == 300.0


@pytest.mark.parametrize(
    ("section", "cle", "valeur"),
    [
        ("moteur", "repeat_penalty", 2.01),
        ("moteur", "repeat_penalty", -0.5),
        ("fiches", "langue", "de"),
        ("ui", "inactivite_moteur_s", 0.0),
        ("ui", "inactivite_moteur_s", -1.0),
        ("fiches", "inconnue", "x"),
    ],
)
def test_bornes_v2_refusees(section, cle, valeur):
    with pytest.raises(ValidationError):
        Configuration.model_validate({section: {cle: valeur}})


@pytest.mark.parametrize("valeur", [0.0, 1.1, 2.0])
def test_repeat_penalty_bornes_admises(valeur):
    assert (
        Configuration.model_validate({"moteur": {"repeat_penalty": valeur}}).moteur.repeat_penalty
        == valeur
    )


def test_langue_en_admise():
    assert Configuration.model_validate({"fiches": {"langue": "en"}}).fiches.langue == "en"


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
