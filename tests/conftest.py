"""Fixtures partagées (contrats §13, AD-10). Aucun test n'écrit dans le var/ du dépôt."""

import tomllib
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from tests.faux_moteur import FauxMoteur, demarrer
from waveaudit.application.config import FICHIER_DEFAUTS, racine_projet
from waveaudit.domaine.configuration import Configuration


@pytest.fixture
def faux_moteur() -> Iterator[Callable[..., FauxMoteur]]:
    """Fabrique : `faux_moteur(scenario="nominal") -> FauxMoteur`, un serveur par appel."""
    arrets: list[Callable[[], None]] = []

    def fabrique(scenario: str = "nominal") -> FauxMoteur:
        moteur, arreter = demarrer(scenario)
        arrets.append(arreter)
        return moteur

    yield fabrique
    for arreter in arrets:
        arreter()


@pytest.fixture
def config_test(tmp_path: Path, faux_moteur: Callable[..., FauxMoteur]) -> Configuration:
    """Configuration de test : mode externe vers un faux moteur nominal, var/ sous tmp_path.

    Part des seuls défauts du dépôt (jamais de `waveaudit.local.toml`). Le catalogue est celui
    du dépôt ; `theme_prive` pointe vers un dossier absent de tmp_path (thème générique).
    """
    racine = racine_projet()
    with (racine / FICHIER_DEFAUTS).open("rb") as fichier:
        donnees = tomllib.load(fichier)
    donnees["moteur"].update(mode="externe", base_url=faux_moteur().base_url, timeout_s=1.0)
    donnees["chemins"] = {
        nom: str(racine / valeur) for nom, valeur in donnees["chemins"].items()
    } | {"var": str(tmp_path / "var"), "theme_prive": str(tmp_path / "theme-prive")}
    return Configuration.model_validate(donnees)
