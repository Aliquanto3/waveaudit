"""Aide partagée `tests/accessibilite.py` (contrats §28 [revue V2]) : chaque règle échoue sur
un HTML ou un CSS fautif écrit à la main, et passe sur sa version corrigée."""

import pytest

from tests.accessibilite import verifier_accessibilite, verifier_focus_css


def _page(corps: str) -> str:
    return f"<!DOCTYPE html><html lang='fr'><body>{corps}</body></html>"


@pytest.mark.parametrize(
    "corps",
    [
        '<input id="nom" type="text"><label for="nom">Nom</label>',
        '<label>Langue <input type="checkbox"></label>',
        '<input type="hidden" name="jeton" value="x">',
        '<input type="submit" value="Lancer">',
        '<a href="/"><img src="/theme/logo.svg" alt="Accueil"></a>',
        '<div role="tab" aria-label="Candidat 1" tabindex="0"></div>',
        '<span id="t">Titre</span><div role="dialog" aria-modal="true" aria-labelledby="t"></div>',
        "<details><summary>Motifs</summary>texte</details>",
        "<span id='a\"b'>X</span><input id='a\"b'><label for='a\"b'>X</label>",
        '<button aria-labelledby="x y"></button><span id="y">Ok</span><span id="x">Go</span>',
    ],
)
def test_html_conforme_accepte(corps):
    verifier_accessibilite(_page(corps))


@pytest.mark.parametrize(
    ("corps", "message"),
    [
        ('<input id="nom" type="text">', "sans nom accessible"),
        ("<button></button>", "sans nom accessible"),
        ('<a href="/"><img src="/x.svg" alt=""></a>', "sans nom accessible"),
        ('<div role="tab" tabindex="0"></div>', "sans nom accessible"),
        ('<li role="option"></li>', "sans nom accessible"),
        ('<div role="checkbox" aria-checked="false"></div>', "sans nom accessible"),
        ("<details><summary></summary></details>", "sans nom accessible"),
        ('<div contenteditable="true"></div>', "sans nom accessible"),
        ('<input type="HIDDEN-NON">', "sans nom accessible"),
        ('<button tabindex="2">Ok</button>', "tabindex positif"),
        ('<span id="t">T</span><div role="dialog" aria-labelledby="t"></div>', "aria-modal"),
        ('<div role="alertdialog" aria-modal="true"></div>', "aria-labelledby"),
        ('<p aria-describedby="absent">x</p>', "id absent"),
        ("<input id='a\"b'>", "sans nom accessible"),
    ],
)
def test_html_fautif_refuse(corps, message):
    with pytest.raises(AssertionError, match=message):
        verifier_accessibilite(_page(corps))


_FOCUS = "button:focus-visible { outline: 2px solid var(--focus-contour); }\n"


@pytest.mark.parametrize(
    "css",
    [
        _FOCUS,
        _FOCUS + "a { outline: none; box-shadow: 0 0 0 2px var(--focus-contour); }",
        _FOCUS + "a:focus { outline: none; outline: 2px solid var(--focus-contour); }",
        _FOCUS + "/* outline: none */ p { color: var(--couleur-encre); }",
    ],
)
def test_css_focus_conforme_accepte(css):
    verifier_focus_css(css)


@pytest.mark.parametrize(
    "css",
    [
        "button:focus { outline: 2px solid var(--focus-contour); }",
        "button:focus-visible { outline: none; border-color: var(--focus-contour); }",
        _FOCUS + "a:focus { outline: none; }",
        _FOCUS + "a:focus { outline: 0; }",
        _FOCUS + "a:focus { outline: 0px !important; }",
        _FOCUS + "a:focus { outline-style: none; }",
        _FOCUS + "a:focus { outline-width: 0; }",
        _FOCUS + "a:focus { outline: none; box-shadow: none; }",
        _FOCUS + "a:focus { outline: 2px solid var(--focus-contour); outline: none; }",
        _FOCUS + "a:focus { outline: none; color: var(--focus-contour); }",
    ],
)
def test_css_focus_fautif_refuse(css):
    with pytest.raises(AssertionError):
        verifier_focus_css(css)
