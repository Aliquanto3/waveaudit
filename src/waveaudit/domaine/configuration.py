"""Modèle de configuration (contrats §2). Le chargement est dans `application/config.py`.

Les défauts reprennent exactement `config/waveaudit.toml`. Les chemins relatifs sont résolus
contre `racine_projet()` par le chargement, jamais contre le dossier courant.
"""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

_CONFIG = ConfigDict(extra="forbid")


class ConfigMoteur(BaseModel):
    model_config = _CONFIG

    mode: Literal["local-gere", "externe"] = "local-gere"
    base_url: str = ""  # externe : URL complète finissant par /v1
    modele: str = ""  # nom d'une entrée du manifeste ; vide = choix auto défaut/repli
    modele_api: str = ""  # champ "model" envoyé ; vide = nom de l'entrée du manifeste
    prefixe_systeme: str = ""  # externe seulement ; en local-gere il vient du manifeste
    cle_api: str = ""  # vide = pas d'en-tête Authorization
    timeout_s: float = 180.0
    temperature: float = 0.2
    seed: int = 42
    max_tokens: int = 700
    longueur_max_rubrique: int = 1200
    taille_max_note: int = 6000  # caractères du corps envoyés au modèle
    ctx: int = 4096
    threads: int = 4
    ram_min_defaut_go: float = 4.5
    delai_demarrage_s: float = 120.0


class ConfigReseau(BaseModel):
    model_config = _CONFIG

    hotes_autorises: list[str] = ["127.0.0.1", "::1", "localhost"]


class ConfigRecherche(BaseModel):
    model_config = _CONFIG

    k1: float = 1.5
    b: float = 0.75


class ConfigChemins(BaseModel):
    model_config = _CONFIG

    var: Path = Path("var")
    catalogue: Path = Path("donnees/catalogue")
    theme_prive: Path = Path("theme-prive")
    manifeste: Path = Path("config/artefacts.toml")


class ConfigUi(BaseModel):
    model_config = _CONFIG

    hote: str = "127.0.0.1"
    port: int = 8765


class Configuration(BaseModel):
    model_config = _CONFIG

    moteur: ConfigMoteur = ConfigMoteur()
    reseau: ConfigReseau = ConfigReseau()
    recherche: ConfigRecherche = ConfigRecherche()
    chemins: ConfigChemins = ConfigChemins()
    ui: ConfigUi = ConfigUi()
