"""Manifeste des artefacts installés (contrats §11, AD-12).

Les chemins ne s'obtiennent que par ce module ; aucune autre partie du code ne doit coder en
dur un chemin sous `var/`.
"""

import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from waveaudit.domaine.erreurs import ConfigurationInvalide

_CONFIG = ConfigDict(extra="forbid")


class Artefact(BaseModel):
    """Une entrée `[[artefact]]` de `config/artefacts.toml`."""

    model_config = _CONFIG

    nom: str
    role: str
    version: str
    url: str
    sha256: str
    taille: int
    licence: str
    source: str
    destination: str
    extraire: bool
    executable: str
    prefixe_systeme: str
    # Facultatifs, modèles seulement. `mode_json` (§22) prime sur `moteur.mode_json`.
    mode_json: Literal["json_schema", "json_object"] | None = None
    # Écart au §22 entériné en v2 : false coupe la réflexion du modèle de discussion.
    reflexion: bool | None = None
    # [v2] 0 < x <= 2.0, prime sur `moteur.repeat_penalty` (§3, §11).
    repeat_penalty: float | None = Field(None, gt=0.0, le=2.0)
    # [v2] Durée médiane par fiche mesurée au banc, affichée par l'UI (§11, §26).
    duree_indicative_s: float | None = Field(None, gt=0.0)


def charger(chemin: Path) -> list[Artefact]:
    """Charge et valide `config/artefacts.toml` (tableau `[[artefact]]`)."""
    try:
        with chemin.open("rb") as fichier:
            donnees = tomllib.load(fichier)
    except FileNotFoundError as erreur:
        raise ConfigurationInvalide(f"manifeste absent : {chemin}") from erreur
    except (OSError, tomllib.TOMLDecodeError) as erreur:
        raise ConfigurationInvalide(f"manifeste illisible ({chemin}) : {erreur}") from erreur
    bruts = donnees.get("artefact", [])
    try:
        artefacts = [Artefact.model_validate(brut) for brut in bruts]
    except ValidationError as erreur:
        raise ConfigurationInvalide(f"manifeste invalide ({chemin}) : {erreur}") from erreur
    if not artefacts:
        raise ConfigurationInvalide(f"manifeste vide : {chemin}")
    return artefacts


def par_nom(artefacts: list[Artefact], nom: str) -> Artefact:
    """L'artefact dont le nom est `nom`."""
    for artefact in artefacts:
        if artefact.nom == nom:
            return artefact
    raise ConfigurationInvalide(f"artefact inconnu dans le manifeste : {nom}")


def par_role(artefacts: list[Artefact], role: str) -> Artefact:
    """L'artefact unique de rôle `role`. Erreur si aucun ou si plusieurs."""
    correspondants = [artefact for artefact in artefacts if artefact.role == role]
    if not correspondants:
        raise ConfigurationInvalide(f"aucun artefact pour le rôle {role}")
    if len(correspondants) > 1:
        raise ConfigurationInvalide(f"rôle non unique dans le manifeste : {role}")
    return correspondants[0]


def chemin(artefact: Artefact, var: Path) -> Path:
    """Chemin final de l'artefact sous `var` (l'exécutable, pour le rôle `moteur`)."""
    base = var / artefact.destination
    if artefact.role == "moteur":
        if not artefact.executable:
            raise ConfigurationInvalide(f"artefact moteur sans executable : {artefact.nom}")
        return base / artefact.executable
    return base
