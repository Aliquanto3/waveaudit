"""Thème générique du rapport Word (contrats §17, AD-14) : aucune charte, couleurs neutres.

Utilisé quand `theme-prive/` est absent, ou en base pour les couleurs de `theme.toml` quand
`theme-prive/` ne fournit pas de `modele.docx`.
"""

import tomllib
from pathlib import Path

from docx import Document
from docx.shared import RGBColor

COULEUR_PRIMAIRE_DEFAUT = "1F3864"
COULEUR_SECONDAIRE_DEFAUT = "44546A"


def document_generique() -> Document:
    """Un `Document()` vierge, stylé de façon neutre (pas de logo, pas de charte)."""
    document = Document()
    appliquer_couleurs(document, COULEUR_PRIMAIRE_DEFAUT, COULEUR_SECONDAIRE_DEFAUT)
    return document


def appliquer_couleurs(document: Document, couleur_primaire: str, couleur_secondaire: str) -> None:
    """Colore les styles de titre existants. Un style absent (modèle privé) est ignoré."""
    for nom, couleur in (
        ("Title", couleur_primaire),
        ("Heading 1", couleur_primaire),
        ("Heading 2", couleur_primaire),
        ("Heading 3", couleur_secondaire),
    ):
        try:
            style = document.styles[nom]
        except KeyError:
            continue
        style.font.color.rgb = RGBColor.from_string(couleur)


def charger_theme(dossier_theme_prive: Path) -> dict[str, str | Path]:
    """Lit `<dossier_theme_prive>/theme.toml` s'il existe. Clés inconnues ignorées.

    Clés reconnues : `couleur_primaire`, `couleur_secondaire` (`#RRGGBB`), `logo` (chemin
    relatif à `dossier_theme_prive`, doit exister). Renvoie `{}` si le fichier est absent.
    """
    fichier = Path(dossier_theme_prive) / "theme.toml"
    if not fichier.is_file():
        return {}
    with fichier.open("rb") as flux:
        brut = tomllib.load(flux)

    theme: dict[str, str | Path] = {}
    for cle in ("couleur_primaire", "couleur_secondaire"):
        valeur = brut.get(cle)
        if isinstance(valeur, str) and valeur:
            theme[cle] = valeur.lstrip("#")
    logo = brut.get("logo")
    if isinstance(logo, str) and logo:
        chemin_logo = Path(dossier_theme_prive) / logo
        if chemin_logo.is_file():
            theme["logo"] = chemin_logo
    return theme
