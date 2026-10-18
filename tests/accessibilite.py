"""Aide d'accessibilité partagée (contrats §28 [revue V2]) : analyse un HTML déjà rendu et
`style.css`, par `lxml.html` (`xpath` seulement, pas de `cssselect`). Utilisée par
`e2e/test_ui.py` (accueil) et les stories suivantes qui ajoutent des écrans (tiroir, onglets,
dialogues) : `e2e/test_relecture_ui.py` (W3b), `e2e/test_incident_ui.py` (W4).
"""

import re

from lxml import html as lxml_html

_XPATH_INTERACTIFS = "//a[@href] | //button | //input | //select | //textarea | //*[@tabindex]"


def _a_nom_accessible(element, arbre, ids: set[str]) -> bool:
    aria_label = (element.get("aria-label") or "").strip()
    if aria_label:
        return True
    aria_labelledby = element.get("aria-labelledby")
    if aria_labelledby and any(cible in ids for cible in aria_labelledby.split()):
        return True
    id_ = element.get("id")
    if id_ and arbre.xpath(f'//label[@for="{id_}"]'):
        return True
    if element.text_content().strip():
        return True
    if element.tag == "input" and (element.get("value") or "").strip():
        if (element.get("type") or "text").lower() in ("submit", "button"):
            return True
    titre = (element.get("title") or "").strip()
    return bool(titre)


def verifier_accessibilite(html: str) -> None:
    """Lève `AssertionError` au premier manquement (contrats §28, analyse du HTML rendu) :

    - chaque élément interactif (`a[href]`, `button`, `input`, `select`, `textarea`,
      `[tabindex]`) a un nom accessible (`label for`, `aria-label`, `aria-labelledby` ou
      texte) ;
    - aucun `tabindex` n'est positif ;
    - chaque `role="dialog"`/`alertdialog` porte `aria-modal="true"` et `aria-labelledby` ;
    - les `id` référencés par un attribut `aria-*` existent dans le document.
    """
    arbre = lxml_html.fromstring(html)
    ids = set(arbre.xpath("//*/@id"))

    for element in arbre.xpath(_XPATH_INTERACTIFS):
        if not _a_nom_accessible(element, arbre, ids):
            extrait = lxml_html.tostring(element, encoding="unicode")[:200]
            raise AssertionError(f"élément interactif sans nom accessible : {extrait}")
        tabindex = element.get("tabindex")
        if tabindex is not None:
            try:
                valeur = int(tabindex)
            except ValueError:
                valeur = 0
            if valeur > 0:
                raise AssertionError(f"tabindex positif ({tabindex!r}) : {element.tag}")

    for element in arbre.xpath('//*[@role="dialog" or @role="alertdialog"]'):
        if element.get("aria-modal") != "true":
            raise AssertionError('dialogue sans aria-modal="true"')
        if not element.get("aria-labelledby"):
            raise AssertionError("dialogue sans aria-labelledby")

    for attribut in ("aria-labelledby", "aria-describedby", "aria-controls", "aria-owns"):
        for element in arbre.xpath(f"//*[@{attribut}]"):
            for cible in element.get(attribut).split():
                if cible not in ids:
                    raise AssertionError(f"{attribut} référence un id absent : {cible}")


_RE_REGLE = re.compile(r"([^{}]+)\{([^{}]*)\}", re.DOTALL)


def verifier_focus_css(css: str) -> None:
    """`style.css` (contrats §28) : une règle `:focus-visible` pose `--focus-contour`, et aucun
    `outline: none` n'est posé sans contour de remplacement (`box-shadow` ou `--focus-contour`
    dans la même règle).
    """
    regles = _RE_REGLE.findall(css)
    if not any(
        ":focus-visible" in selecteur and "--focus-contour" in corps for selecteur, corps in regles
    ):
        raise AssertionError("aucune règle :focus-visible n'utilise --focus-contour")
    for selecteur, corps in regles:
        if re.search(r"outline\s*:\s*none", corps, re.IGNORECASE):
            if "box-shadow" not in corps and "--focus-contour" not in corps:
                raise AssertionError(
                    f"outline: none sans contour de remplacement dans « {selecteur.strip()} »"
                )
