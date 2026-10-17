"""Thème générique du rapport Word (contrats §17, AD-14) : aucune charte, couleurs neutres.

Utilisé quand `theme-prive/` est absent, ou en base pour les couleurs de `theme.toml` quand
`theme-prive/` ne fournit pas de `modele.docx`.
"""

import re
import tomllib
from pathlib import Path

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.shared import Pt, RGBColor

from waveaudit.domaine.erreurs import ConfigurationInvalide

COULEUR_PRIMAIRE_DEFAUT = "1F3864"
COULEUR_SECONDAIRE_DEFAUT = "44546A"

_COULEUR = re.compile(r"#?[0-9A-Fa-f]{6}")
# Styles de titre utilisés par l'export ; un modèle Word ne définit que les styles qu'il emploie.
_STYLES_TITRE: dict[str, int] = {"Title": 26, "Heading 1": 16, "Heading 2": 14, "Heading 3": 12}


def document_generique() -> Document:
    """Un `Document()` vierge, stylé de façon neutre (pas de logo, pas de charte)."""
    document = Document()
    appliquer_couleurs(document, COULEUR_PRIMAIRE_DEFAUT, COULEUR_SECONDAIRE_DEFAUT)
    return document


def assurer_styles_titre(document: Document) -> None:
    """Ajoute les styles de titre absents d'un modèle privé (sinon `add_heading` lève KeyError)."""
    noms = {style.name for style in document.styles}
    for nom, taille in _STYLES_TITRE.items():
        if nom in noms:
            continue
        style = document.styles.add_style(nom, WD_STYLE_TYPE.PARAGRAPH)
        style.base_style = document.styles["Normal"]
        style.font.bold = True
        style.font.size = Pt(taille)


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
    Lève `ConfigurationInvalide` si le fichier est illisible ou si une couleur n'est pas
    `#RRGGBB`.
    """
    fichier = Path(dossier_theme_prive) / "theme.toml"
    if not fichier.is_file():
        return {}
    try:
        with fichier.open("rb") as flux:
            brut = tomllib.load(flux)
    except (OSError, tomllib.TOMLDecodeError) as erreur:
        raise ConfigurationInvalide(
            f"{fichier.name} du thème privé illisible : {erreur}"
        ) from erreur

    theme: dict[str, str | Path] = {}
    for cle in ("couleur_primaire", "couleur_secondaire"):
        valeur = brut.get(cle)
        if valeur is None:
            continue
        if not isinstance(valeur, str) or not _COULEUR.fullmatch(valeur):
            raise ConfigurationInvalide(
                f"{fichier.name} du thème privé : {cle} doit être de la forme #RRGGBB, "
                f"reçu {valeur!r}"
            )
        theme[cle] = valeur.lstrip("#").upper()
    logo = brut.get("logo")
    if isinstance(logo, str) and logo:
        chemin_logo = Path(dossier_theme_prive) / logo
        if chemin_logo.is_file():
            theme["logo"] = chemin_logo
    return theme
