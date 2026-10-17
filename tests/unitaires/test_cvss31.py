import pytest

from waveaudit.domaine.cvss31 import evaluer
from waveaudit.domaine.erreurs import EntreeInvalide


@pytest.mark.parametrize(
    ("vecteur", "score", "severite"),
    [
        ("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H", 9.8, "critique"),
        ("CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N", 6.1, "moyenne"),
        ("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:N", 0.0, "aucune"),
        ("CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:U/C:L/I:N/A:N", 3.1, "faible"),
        ("CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H", 8.8, "elevee"),
    ],
)
def test_evaluer_vecteurs_reference_first(vecteur, score, severite):
    resultat = evaluer(vecteur)
    assert resultat.vecteur == vecteur
    assert resultat.score == score
    assert resultat.severite == severite


def test_evaluer_vecteur_malforme_leve_entree_invalide():
    with pytest.raises(EntreeInvalide):
        evaluer("CVSS:3.1/AV:X/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H")


def test_evaluer_vecteur_incomplet_leve_entree_invalide():
    with pytest.raises(EntreeInvalide):
        evaluer("CVSS:3.1/AV:N/AC:L")
