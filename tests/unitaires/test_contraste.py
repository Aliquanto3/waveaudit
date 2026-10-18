"""Contrastes WCAG des tokens (contrats §28 [revue V2]) : recalcule chaque ratio texte/fond
déclaré dans `DESIGN.md` à partir des couleurs effectivement publiées par `tokens.css`, et
vérifie qu'il atteint le seuil AA (4,5:1 pour du texte, 3:1 pour le contour de focus) et qu'il
égale à 0,1 près le ratio annoncé par `DESIGN.md`. Une couleur de `tokens.css` qui s'écarte de
`DESIGN.md` fait échouer ce test (c'est le but : les deux fichiers ne peuvent plus diverger en
silence).
"""

import re
from pathlib import Path

import yaml

RACINE_WEB = Path(__file__).resolve().parents[2] / "src" / "waveaudit" / "interfaces" / "web"
TOKENS_CSS = RACINE_WEB / "static" / "tokens.css"

BLANC = "#FFFFFF"

# Paires texte/fond déclarées dans DESIGN.md (section Colors et table « Rôle dérivé »), avec le
# ratio qui y est annoncé. `seuil` : 4,5 pour du texte, 3 pour le contour de focus (ce dernier
# réutilise `primaire`, déjà bien au-dessus du seuil texte).
PAIRES = [
    ("primaire", BLANC, 9.3, 4.5),
    ("primaire", "primaire-doux", 7.7, 4.5),
    (BLANC, "primaire-fonce", 15.4, 4.5),
    ("encre", BLANC, 19.7, 4.5),
    ("encre-douce", BLANC, 8.6, 4.5),
    ("accent-texte", BLANC, 6.6, 4.5),
    ("accent-texte", "accent-doux", 5.9, 4.5),
    ("gris-texte", BLANC, 5.8, 4.5),
    ("gris-texte", "fond-creme", 5.3, 4.5),
    ("attention-texte", BLANC, 5.9, 4.5),
    ("attention-texte", "attention-doux", 5.0, 4.5),
    ("danger-texte", BLANC, 6.5, 4.5),
    ("danger-texte", "danger-doux", 5.1, 4.5),
    ("texte-sur-vif", "accent", 12.8, 4.5),
    ("texte-sur-vif", "attention", 12.9, 4.5),
    ("texte-sur-vif", "danger", 5.3, 4.5),
    # Contour de focus (DESIGN.md « Focus visible ») : seuil non-texte 3:1.
    ("primaire", BLANC, 9.3, 3.0),
]

_RE_TOKEN = re.compile(r"--couleur-([a-z-]+)\s*:\s*(#[0-9A-Fa-f]{6})")


def _lire_couleurs() -> dict[str, str]:
    texte = TOKENS_CSS.read_text(encoding="utf-8")
    couleurs = {nom: valeur.upper() for nom, valeur in _RE_TOKEN.findall(texte)}
    couleurs[BLANC] = BLANC
    return couleurs


def _luminance(hexv: str) -> float:
    hexv = hexv.lstrip("#")
    r, g, b = (int(hexv[i : i + 2], 16) / 255 for i in (0, 2, 4))

    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def _ratio(a: str, b: str) -> float:
    l1, l2 = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def test_tokens_css_declare_toutes_les_couleurs_des_paires():
    couleurs = _lire_couleurs()
    manquants = {fg for fg, _, _, _ in PAIRES if fg not in couleurs} | {
        bg for _, bg, _, _ in PAIRES if bg not in couleurs
    }
    assert manquants == set()


def test_contrastes_wcag_conformes_a_design_md():
    couleurs = _lire_couleurs()
    fautes = []
    for fg, bg, attendu, seuil in PAIRES:
        ratio = _ratio(couleurs[fg], couleurs[bg])
        if ratio < seuil:
            fautes.append(f"{fg}/{bg} : {ratio:.2f} sous le seuil {seuil}")
        if abs(ratio - attendu) > 0.1:
            fautes.append(f"{fg}/{bg} : {ratio:.2f} ≠ {attendu} annoncé par DESIGN.md")
    assert fautes == []


DESIGN_MD = Path(__file__).resolve().parents[2] / "_bmad-output/planning-artifacts/ux/DESIGN.md"
STYLE_CSS = RACINE_WEB / "static" / "style.css"
# Tokens hors de la clé `colors` de DESIGN.md, mais référence implicite de ses ratios.
_TOKENS_HORS_DESIGN = {"blanc": BLANC}


def _couleurs_design_md() -> dict[str, str]:
    texte = DESIGN_MD.read_text(encoding="utf-8")
    entete = yaml.safe_load(texte.split("---")[1])
    return {nom: str(valeur).upper() for nom, valeur in entete["colors"].items()}


def test_tokens_css_egale_exactement_les_couleurs_de_design_md():
    """§28 : une couleur de `tokens.css` différente de `DESIGN.md` fait échouer le test, même
    si son ratio reste à 0,1 près du ratio annoncé."""
    publiees = {
        nom: valeur.upper() for nom, valeur in _RE_TOKEN.findall(TOKENS_CSS.read_text("utf-8"))
    }
    assert publiees == _couleurs_design_md() | _TOKENS_HORS_DESIGN


def test_style_css_sans_couleur_litterale():
    """§28 : `style.css` n'utilise que les propriétés de `tokens.css` pour les couleurs."""
    css = re.sub(r"/\*.*?\*/", "", STYLE_CSS.read_text(encoding="utf-8"), flags=re.DOTALL)
    litterales = re.findall(r"#[0-9A-Fa-f]{3,8}\b|\b(?:rgba?|hsla?)\(|:\s*(?:white|black)\b", css)
    assert litterales == []
