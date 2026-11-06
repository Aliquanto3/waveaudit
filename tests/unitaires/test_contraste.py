"""Charte générique v2.1 de l'interface web : contrastes WCAG et règles de `style.css`.

Les jetons viennent de `tokens.css` (copie de `charte-generique/dist/charte.css`), dans les deux
thèmes : sombre en `:root`, clair sous `prefers-color-scheme: light` et `[data-theme="light"]`.
Bibliothèque standard seulement. Seuils : 4,5:1 pour le texte ; 3:1 pour `trait-fort`, `focus` et
les marques non textuelles (pictogramme, contours d'état).
"""

import hashlib
import re
from pathlib import Path

RACINE_WEB = Path(__file__).resolve().parents[2] / "src" / "pentest_scribe" / "interfaces" / "web"
TOKENS_CSS = RACINE_WEB / "static" / "tokens.css"
STYLE_CSS = RACINE_WEB / "static" / "style.css"
BASE_HTML = RACINE_WEB / "templates" / "base.html"

# Couples (texte, fond) réellement utilisés par `style.css`, seuil 4,5:1.
PAIRES_TEXTE = [
    ("texte", "fond"),  # body
    ("texte", "surface"),  # en-tête, cartes, onglets, boîtes de dialogue
    ("texte", "surface-alt"),  # panneau de note, carte de workflow choisie
    ("texte", "primaire-doux"),  # ligne sélectionnée du tiroir
    ("texte-attenue", "fond"),  # libellés, indicateur d'enregistrement
    ("texte-attenue", "surface"),
    ("texte-attenue", "surface-alt"),  # bouton désactivé
    ("primaire", "fond"),  # liens
    ("primaire", "surface"),  # onglet choisi
    ("primaire-vif", "fond"),  # liens au survol
    ("sur-bouton", "bouton"),  # bouton principal et bouton à bascule enfoncé
    ("sur-bouton", "bouton-survol"),
    ("sur-encre", "encre-pleine"),  # bandeau
    ("accent-texte", "accent-doux"),  # pastille de sévérité faible
    ("alerte-texte", "alerte-doux"),  # pastille moyenne, bandeau de motifs
    ("erreur", "erreur-doux"),  # pastille élevée
    ("sur-statut", "erreur"),  # pastille critique
]

# Couples (marque, fond) non textuels, seuil 3:1.
PAIRES_NON_TEXTE = [
    ("trait-fort", "surface"),  # contour des boutons, du tiroir, des boîtes
    ("trait-fort", "fond"),
    ("focus", "surface"),
    ("focus", "fond"),
    ("focus", "surface-alt"),
    ("primaire", "surface"),  # contour de l'onglet choisi
    ("erreur", "surface"),  # champ CVSS invalide
    ("alerte-texte", "alerte-doux"),  # contour du bandeau de motifs
    ("alerte-texte", "fond"),
    ("bouton", "fond"),  # contour de la carte de workflow choisie
    ("accent", "fond"),  # filet or sous le titre
    ("picto-tuile", "surface"),  # pictogramme de l'en-tête
    ("picto-barres", "picto-tuile"),
    ("picto-point", "picto-tuile"),
]

_RE_VAR = re.compile(r"--([a-z0-9-]+)\s*:\s*(#[0-9A-Fa-f]{6})\s*;")

# Empreinte des 212 couples `--jeton: #RRGGBB` de `dist/charte.css` v2.1.0, dans l'ordre du
# fichier. Pour passer à une nouvelle version : recopier le `dist/charte.css` de
# charte-generique dans `tokens.css` (en gardant l'en-tête et les @font-face), puis remplacer
# cette valeur par celle qu'affiche l'échec du test.
EMPREINTE_JETONS_V21 = "d6d7280a114ae1075e84ba74801586fe01c835c393d8f8a949b61c0e83e87cd4"


def _bloc(css: str, ouverture: str) -> str:
    debut = css.index(ouverture) + len(ouverture)
    fin = css.index("\n}", debut)
    return css[debut:fin]


def _themes() -> dict[str, dict[str, str]]:
    css = TOKENS_CSS.read_text(encoding="utf-8")
    sombre = _bloc(css, ":root {")
    clair = _bloc(css, '[data-theme="clair"],\n[data-theme="light"] {')
    return {
        nom: {cle: valeur.upper() for cle, valeur in _RE_VAR.findall(bloc)}
        for nom, bloc in (("sombre", sombre), ("clair", clair))
    }


def _resoudre(theme: dict[str, str], nom: str) -> str:
    # Les trois alias du pictogramme pointent vers d'autres jetons.
    alias = {
        "picto-tuile": "pictogramme-tuile",
        "picto-barres": "sur-primaire",
        "picto-point": "pictogramme-point",
    }
    return theme[alias.get(nom, nom)]


def _luminance(hexv: str) -> float:
    hexv = hexv.lstrip("#")
    r, g, b = (int(hexv[i : i + 2], 16) / 255 for i in (0, 2, 4))

    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def _ratio(a: str, b: str) -> float:
    l1, l2 = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def _fautes(paires: list[tuple[str, str]], seuil: float) -> list[str]:
    fautes = []
    for nom_theme, theme in _themes().items():
        for avant, fond in paires:
            ratio = _ratio(_resoudre(theme, avant), _resoudre(theme, fond))
            if ratio < seuil:
                fautes.append(f"{nom_theme} : {avant}/{fond} = {ratio:.2f} < {seuil}")
    return fautes


def test_les_deux_themes_definissent_les_memes_jetons_et_des_valeurs_differentes():
    themes = _themes()
    assert set(themes["sombre"]) == set(themes["clair"])
    assert themes["sombre"]["fond"] == "#0F1318"
    assert themes["clair"]["fond"] == "#F6F8FB"
    assert themes["sombre"]["texte"] != themes["clair"]["texte"]


def test_le_bloc_media_clair_egale_le_theme_clair_force():
    css = TOKENS_CSS.read_text(encoding="utf-8")
    media = _bloc(
        css,
        "@media (prefers-color-scheme: light) {\n"
        '  :root:not([data-theme="sombre"]):not([data-theme="dark"]) {',
    )
    media_vars = {cle: valeur.upper() for cle, valeur in _RE_VAR.findall(media)}
    assert media_vars == _themes()["clair"]
    assert media_vars["fond"] == "#F6F8FB"


def test_tokens_css_reprend_les_valeurs_de_la_charte_v21():
    couples = _RE_VAR.findall(TOKENS_CSS.read_text(encoding="utf-8"))
    texte = "\n".join(f"{cle}:{valeur.upper()}" for cle, valeur in couples)
    empreinte = hashlib.sha256(texte.encode()).hexdigest()
    assert empreinte == EMPREINTE_JETONS_V21, (
        f"tokens.css s'écarte de dist/charte.css v2.1.0 ({len(couples)} couples, empreinte "
        f"{empreinte}) : voir le commentaire d'EMPREINTE_JETONS_V21"
    )


def test_le_sombre_est_le_defaut_et_data_theme_force_les_deux_themes():
    css = TOKENS_CSS.read_text(encoding="utf-8")
    assert css.index("\n:root {") < css.index("@media (prefers-color-scheme: light)")
    assert '[data-theme="sombre"],\n[data-theme="dark"]' in css
    assert '[data-theme="clair"],\n[data-theme="light"]' in css


def test_contrastes_du_texte_dans_les_deux_themes():
    assert _fautes(PAIRES_TEXTE, 4.5) == []


def test_contrastes_non_textuels_dans_les_deux_themes():
    assert _fautes(PAIRES_NON_TEXTE, 3.0) == []


def test_style_css_sans_couleur_litterale():
    """`style.css` n'emploie que les jetons de `tokens.css` pour les couleurs."""
    css = re.sub(r"/\*.*?\*/", "", STYLE_CSS.read_text(encoding="utf-8"), flags=re.DOTALL)
    litterales = re.findall(r"#[0-9A-Fa-f]{3,8}\b|\b(?:rgba?|hsla?)\(|:\s*(?:white|black)\b", css)
    assert litterales == []


def test_style_css_ne_cite_que_des_jetons_definis():
    css = re.sub(r"/\*.*?\*/", "", STYLE_CSS.read_text(encoding="utf-8"), flags=re.DOTALL)
    definis = set(_themes()["sombre"]) | set(
        re.findall(r"--([a-z0-9-]+)\s*:", TOKENS_CSS.read_text(encoding="utf-8"))
    )
    utilises = set(re.findall(r"var\(--([a-z0-9-]+)", css))
    assert utilises - definis == set()


def test_le_bleu_n_est_jamais_un_aplat_de_bouton():
    css = re.sub(r"/\*.*?\*/", "", STYLE_CSS.read_text(encoding="utf-8"), flags=re.DOTALL)
    fautes = []
    for selecteur, corps in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        if (
            "button" not in selecteur
            and "carte-workflow" not in selecteur
            and '[role="tab"]' not in selecteur
        ):
            continue
        for declaration in corps.split(";"):
            # `primaire-doux` reste permis : c'est le fond de sélection de la charte.
            if re.match(
                r"\s*background(-color)?\s*:.*var\(--primaire(?!-doux\))[a-z-]*\)", declaration
            ):
                fautes.append(selecteur.strip())
    assert fautes == []


def test_le_bouton_principal_est_neutre_et_le_secondaire_en_contour():
    css = STYLE_CSS.read_text(encoding="utf-8")
    principal = re.search(
        r'button\[type="submit"\]:not\(:disabled\),.*?\{([^}]*)\}', css, re.DOTALL
    )
    assert principal is not None
    assert "background: var(--bouton)" in principal.group(1)
    assert "color: var(--sur-bouton)" in principal.group(1)
    defaut = re.search(r"\nbutton \{([^}]*)\}", css)
    assert defaut is not None
    assert "border: 1px solid var(--trait-fort)" in defaut.group(1)
    assert "background: var(--surface)" in defaut.group(1)


def test_focus_en_jeton_focus_et_liens_soulignes():
    css = STYLE_CSS.read_text(encoding="utf-8")
    assert "outline: var(--focus-largeur) solid var(--focus);" in css
    assert re.search(r"\na \{[^}]*text-decoration: underline", css)


def test_polices_de_la_charte_servies_localement():
    css = TOKENS_CSS.read_text(encoding="utf-8")
    for famille in ("Sora", "Atkinson Hyperlegible", "JetBrains Mono"):
        assert f"font-family: '{famille}';" in css
    for fichier in re.findall(r"url\('/static/polices/([^']+)'\)", css):
        assert (RACINE_WEB / "static" / "polices" / fichier).is_file()
    assert (RACINE_WEB / "static" / "polices" / "OFL-sora.txt").is_file()


def test_le_gabarit_pose_le_favicon_et_le_pictogramme_par_jetons():
    html = BASE_HTML.read_text(encoding="utf-8")
    assert 'rel="icon" href="/static/favicon.svg"' in html
    assert "var(--picto-tuile)" in STYLE_CSS.read_text(encoding="utf-8")
    assert "style=" not in html
    assert not re.search(r"#[0-9A-Fa-f]{6}", html)
