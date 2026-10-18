"""Aide d'accessibilité partagée (contrats §28 [revue V2]) : analyse un HTML déjà rendu et
`style.css`, par `lxml.html` (`xpath` seulement, pas de `cssselect`). Utilisée par
`e2e/test_ui.py` (accueil) et les stories suivantes qui ajoutent des écrans (tiroir, onglets,
dialogues) : `e2e/test_relecture_ui.py` (W3b), `e2e/test_incident_ui.py` (W4).

`lxml` est une dépendance transitive (python-docx) : import direct toléré dans les tests.
"""

import re

from lxml import html as lxml_html

# Rôles ARIA de widgets interactifs (WAI-ARIA 1.2, « widget roles ») : un élément qui les porte
# est interactif même s'il n'est pas un contrôle natif (onglets, options du tiroir…).
_ROLES_INTERACTIFS = (
    "button",
    "checkbox",
    "combobox",
    "link",
    "listbox",
    "menuitem",
    "menuitemcheckbox",
    "menuitemradio",
    "option",
    "radio",
    "searchbox",
    "slider",
    "spinbutton",
    "switch",
    "tab",
    "textbox",
    "treeitem",
)
_XPATH_INTERACTIFS = (
    "//a[@href] | //button | //input[not(translate(@type, 'HIDEN', 'hiden') = 'hidden')]"
    " | //select | //textarea | //summary | //*[@tabindex] | //*[@contenteditable]"
    " | //*[@role][contains(concat(' ', $roles, ' '), concat(' ', normalize-space(@role), ' '))]"
)


def _a_nom_accessible(element, arbre, ids: set[str]) -> bool:
    if (element.get("aria-label") or "").strip():
        return True
    aria_labelledby = element.get("aria-labelledby")
    if aria_labelledby and any(cible in ids for cible in aria_labelledby.split()):
        return True
    id_ = element.get("id")
    if id_ and arbre.xpath("//label[@for=$i]", i=id_):
        return True
    if element.xpath("ancestor::label"):
        return True
    if element.text_content().strip():
        return True
    # Image porteuse du nom (lien ou bouton iconographique) : `alt` non vide.
    if any((alt or "").strip() for alt in element.xpath(".//img/@alt")):
        return True
    if element.tag == "input":
        type_ = (element.get("type") or "text").lower()
        if type_ in ("submit", "reset", "button") and (element.get("value") or "").strip():
            return True
        if type_ == "image" and (element.get("alt") or "").strip():
            return True
    return bool((element.get("title") or "").strip())


def verifier_accessibilite(html: str) -> None:
    """Lève `AssertionError` au premier manquement (contrats §28, analyse du HTML rendu) :

    - chaque élément interactif (`a[href]`, `button`, `input` non caché, `select`,
      `textarea`, `summary`, `[tabindex]`, `[contenteditable]`, rôle ARIA de widget) a un nom
      accessible (`label for` ou englobant, `aria-label`, `aria-labelledby`, texte, `alt`
      d'une image, `title`) ;
    - aucun `tabindex` n'est positif ;
    - chaque `role="dialog"`/`alertdialog` porte `aria-modal="true"` et `aria-labelledby` ;
    - les `id` référencés par un attribut `aria-*` existent dans le document.
    """
    arbre = lxml_html.fromstring(html)
    ids = set(arbre.xpath("//*/@id"))

    for element in arbre.xpath(_XPATH_INTERACTIFS, roles=" ".join(_ROLES_INTERACTIFS)):
        if not _a_nom_accessible(element, arbre, ids):
            extrait = lxml_html.tostring(element, encoding="unicode")[:200]
            raise AssertionError(f"élément interactif sans nom accessible : {extrait}")
        tabindex = element.get("tabindex")
        if tabindex is not None:
            try:
                valeur = int(tabindex.strip())
            except ValueError:
                valeur = 0
            if valeur > 0:
                raise AssertionError(f"tabindex positif ({tabindex!r}) : {element.tag}")

    for element in arbre.xpath('//*[@role="dialog" or @role="alertdialog"]'):
        if element.get("aria-modal") != "true":
            raise AssertionError('dialogue sans aria-modal="true"')
        if not (element.get("aria-labelledby") or "").strip():
            raise AssertionError("dialogue sans aria-labelledby")

    for attribut in (
        "aria-labelledby",
        "aria-describedby",
        "aria-controls",
        "aria-owns",
        "aria-activedescendant",
        "aria-errormessage",
    ):
        for element in arbre.xpath(f"//*[@{attribut}]"):
            for cible in element.get(attribut).split():
                if cible not in ids:
                    raise AssertionError(f"{attribut} référence un id absent : {cible}")


_RE_COMMENTAIRE = re.compile(r"/\*.*?\*/", re.DOTALL)
_RE_REGLE = re.compile(r"([^{}]+)\{([^{}]*)\}", re.DOTALL)
# Valeur qui retire le contour : `none` ou `0` (avec ou sans unité), `!important` permis.
_VALEURS_SANS_CONTOUR = re.compile(r"^(none|0(\.0+)?[a-z%]*)(\s*!important)?$", re.IGNORECASE)


def _declarations(corps: str) -> list[tuple[str, str]]:
    paires = []
    for morceau in corps.split(";"):
        if ":" in morceau:
            nom, valeur = morceau.split(":", 1)
            paires.append((nom.strip().lower(), valeur.strip()))
    return paires


def _retire_le_contour(nom: str, valeur: str) -> bool:
    if nom not in ("outline", "outline-style", "outline-width"):
        return False
    if nom == "outline-style":
        return valeur.lower().startswith("none")
    return bool(_VALEURS_SANS_CONTOUR.match(valeur))


def _contour_focus(nom: str, valeur: str) -> bool:
    return nom == "outline" and "var(--focus-contour" in valeur


def verifier_focus_css(css: str) -> None:
    """`style.css` (contrats §28) : une règle `:focus-visible` pose `outline` avec
    `var(--focus-contour)`, et aucune règle ne retire le contour (`outline: none` ou `0`,
    `outline-style: none`, `outline-width: 0`) sans contour de remplacement dans
    la même règle (`box-shadow` non nul, ou `outline` avec `var(--focus-contour)` posé après).
    """
    regles = _RE_REGLE.findall(_RE_COMMENTAIRE.sub("", css))
    if not any(
        ":focus-visible" in selecteur and any(_contour_focus(n, v) for n, v in _declarations(corps))
        for selecteur, corps in regles
    ):
        raise AssertionError("aucune règle :focus-visible n'utilise var(--focus-contour)")
    for selecteur, corps in regles:
        declarations = _declarations(corps)
        ombre = any(n == "box-shadow" and not v.lower().startswith("none") for n, v in declarations)
        retire = False
        for nom, valeur in declarations:
            if _retire_le_contour(nom, valeur):
                retire = True
            elif _contour_focus(nom, valeur):
                retire = False
        if retire and not ombre:
            raise AssertionError(f"contour retiré sans remplacement dans « {selecteur.strip()} »")
