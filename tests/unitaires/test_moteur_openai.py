"""Tests de l'adaptateur moteur compatible OpenAI (contrats §3, AD-3)."""

import json
from collections.abc import Callable

import pytest

from tests.faux_moteur import FauxMoteur
from waveaudit.adaptateurs.moteur_openai import MoteurOpenAI
from waveaudit.domaine.erreurs import MoteurInjoignable, SortieInvalide
from waveaudit.domaine.modeles import schema_sortie
from waveaudit.domaine.ports import Message

_CONSTAT = json.dumps(
    {
        "id": "WEB-001",
        "titre": "Titre du constat",
        "description": "Description du constat.",
        "impact": "Impact du constat.",
        "recommandation": "Recommandation du constat.",
        "cvss_vecteur": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
    },
    ensure_ascii=False,
)
MESSAGES: list[Message] = [
    {"role": "system", "content": "consigne"},
    {"role": "user", "content": f"<constat>{_CONSTAT}</constat>"},
]
SCHEMA = schema_sortie(1200)


def _moteur(fm: FauxMoteur, **kwargs: object) -> MoteurOpenAI:
    return MoteurOpenAI(fm.base_url, "mon-modele-api", **kwargs)


def test_nominal_corps_de_requete_conforme(faux_moteur: Callable[..., FauxMoteur]) -> None:
    fm = faux_moteur("nominal")
    moteur = _moteur(fm, temperature=0.3, seed=7)
    sortie = moteur.generer_json(MESSAGES, SCHEMA, max_tokens=321)

    assert isinstance(sortie, dict)
    assert len(fm.requetes) == 1
    corps = fm.requetes[0]
    assert corps["model"] == "mon-modele-api"
    assert corps["messages"] == MESSAGES
    assert corps["temperature"] == 0.3
    assert corps["seed"] == 7
    assert corps["max_tokens"] == 321
    rf = corps["response_format"]
    assert rf["type"] == "json_schema"
    assert rf["json_schema"]["name"] == "sortie_fiche"
    assert rf["json_schema"]["strict"] is True
    assert rf["json_schema"]["schema"] == SCHEMA


def test_json_invalide_leve_sortie_invalide(faux_moteur: Callable[..., FauxMoteur]) -> None:
    fm = faux_moteur("json_invalide")
    moteur = _moteur(fm)
    with pytest.raises(SortieInvalide):
        moteur.generer_json(MESSAGES, SCHEMA, max_tokens=100)


def test_erreur_500_leve_moteur_injoignable(faux_moteur: Callable[..., FauxMoteur]) -> None:
    fm = faux_moteur("erreur_500")
    moteur = _moteur(fm)
    with pytest.raises(MoteurInjoignable):
        moteur.generer_json(MESSAGES, SCHEMA, max_tokens=100)


def test_injoignable_leve_moteur_injoignable(faux_moteur: Callable[..., FauxMoteur]) -> None:
    fm = faux_moteur("injoignable")
    moteur = _moteur(fm)
    with pytest.raises(MoteurInjoignable):
        moteur.generer_json(MESSAGES, SCHEMA, max_tokens=100)


def test_injoignable_sonder_leve_moteur_injoignable(faux_moteur: Callable[..., FauxMoteur]) -> None:
    fm = faux_moteur("injoignable")
    moteur = _moteur(fm)
    with pytest.raises(MoteurInjoignable):
        moteur.sonder()


def test_lent_avec_timeout_court_leve_moteur_injoignable(
    faux_moteur: Callable[..., FauxMoteur],
) -> None:
    fm = faux_moteur("lent")
    moteur = _moteur(fm, timeout_s=1.0)
    with pytest.raises(MoteurInjoignable):
        moteur.generer_json(MESSAGES, SCHEMA, max_tokens=100)


def test_sonder_ok(faux_moteur: Callable[..., FauxMoteur]) -> None:
    fm = faux_moteur("nominal")
    moteur = _moteur(fm)
    moteur.sonder()  # ne doit pas lever


def test_authorization_absent_si_cle_api_vide(faux_moteur: Callable[..., FauxMoteur]) -> None:
    fm = faux_moteur("nominal")
    moteur = _moteur(fm, cle_api="")
    assert "authorization" not in moteur._client.headers


def test_authorization_present_si_cle_api_fournie(faux_moteur: Callable[..., FauxMoteur]) -> None:
    fm = faux_moteur("nominal")
    moteur = _moteur(fm, cle_api="secret")
    assert moteur._client.headers["authorization"] == "Bearer secret"


def test_trust_env_false_ignore_un_proxy_bidon(
    faux_moteur: Callable[..., FauxMoteur], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1/")
    fm = faux_moteur("nominal")
    moteur = _moteur(fm)
    moteur.sonder()  # réussit : le proxy bidon n'est pas utilisé
