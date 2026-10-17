"""Chargement de la configuration (contrats §2, AD-13). Seul lecteur de configuration."""

import tomllib
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from waveaudit.domaine.configuration import Configuration
from waveaudit.domaine.erreurs import ConfigurationInvalide

FICHIER_DEFAUTS = Path("config") / "waveaudit.toml"
FICHIER_LOCAL = "waveaudit.local.toml"


def racine_projet() -> Path:
    """Dossier qui contient `config/waveaudit.toml`, cherché depuis l'emplacement du paquet."""
    for dossier in Path(__file__).resolve().parents:
        if (dossier / FICHIER_DEFAUTS).is_file():
            return dossier
    raise ConfigurationInvalide(f"{FICHIER_DEFAUTS} introuvable au-dessus de {Path(__file__)}")


def _lire_toml(chemin: Path) -> dict[str, Any]:
    try:
        with chemin.open("rb") as fichier:
            return tomllib.load(fichier)
    except FileNotFoundError as erreur:
        raise ConfigurationInvalide(f"fichier de configuration absent : {chemin}") from erreur
    except (OSError, tomllib.TOMLDecodeError) as erreur:
        raise ConfigurationInvalide(f"configuration illisible ({chemin}) : {erreur}") from erreur


def _fusionner(base: dict[str, Any], surcharge: dict[str, Any]) -> dict[str, Any]:
    resultat = dict(base)
    for cle, valeur in surcharge.items():
        if isinstance(valeur, dict) and isinstance(resultat.get(cle), dict):
            resultat[cle] = _fusionner(resultat[cle], valeur)
        else:
            resultat[cle] = valeur
    return resultat


def charger_configuration(chemin: Path | None = None) -> Configuration:
    """Défauts, puis `waveaudit.local.toml` s'il existe, puis `chemin` ; fusion profonde.

    Les chemins relatifs de `[chemins]` sont résolus contre `racine_projet()`.
    """
    racine = racine_projet()
    donnees = _lire_toml(racine / FICHIER_DEFAUTS)
    local = racine / FICHIER_LOCAL
    if local.is_file():
        donnees = _fusionner(donnees, _lire_toml(local))
    if chemin is not None:
        donnees = _fusionner(donnees, _lire_toml(Path(chemin)))
    try:
        config = Configuration.model_validate(donnees)
    except ValidationError as erreur:
        details = "; ".join(
            f"{'.'.join(str(p) for p in e['loc'])} : {e['msg']}" for e in erreur.errors()
        )
        raise ConfigurationInvalide(f"configuration invalide : {details}") from erreur
    chemins = {
        nom: valeur if valeur.is_absolute() else racine / valeur
        for nom, valeur in config.chemins.model_dump().items()
    }
    return config.model_copy(update={"chemins": config.chemins.model_copy(update=chemins)})
