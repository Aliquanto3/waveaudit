import json

import httpx
import pytest

from tests.faux_moteur import REFERENCES_INVENTEES

CONSTAT = {
    "id": "WEB-XSS-REFLECHI",
    "titre": "XSS réfléchi",
    "description": "Description type.",
    "impact": "Impact type.",
    "recommandation": "Recommandation type.",
    "cvss_vecteur": "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N",
}
CORPS = {
    "model": "m",
    "messages": [
        {"role": "system", "content": "consigne"},
        {
            "role": "user",
            "content": f"<constat>{json.dumps(CONSTAT, ensure_ascii=False)}</constat>"
            "<note>Actif : app.exemple.test\nobservations</note>",
        },
    ],
}


def _client(timeout: float = 5.0) -> httpx.Client:
    return httpx.Client(trust_env=False, timeout=timeout)


def _contenu(base_url: str) -> str:
    with _client() as client:
        reponse = client.post(f"{base_url}/chat/completions", json=CORPS)
    assert reponse.status_code == 200
    return reponse.json()["choices"][0]["message"]["content"]


def _sortie_attendue() -> dict:
    sortie = {r: "[adapté] " + CONSTAT[r] for r in ("titre", "description", "impact")}
    sortie["recommandation"] = "[adapté] " + CONSTAT["recommandation"]
    sortie["cvss"] = {
        "AV": "N",
        "AC": "L",
        "PR": "N",
        "UI": "R",
        "S": "C",
        "C": "L",
        "I": "L",
        "A": "N",
    }
    return sortie


def test_nominal_routes_et_requetes(faux_moteur):
    moteur = faux_moteur()
    assert moteur.base_url.startswith("http://127.0.0.1:") and moteur.base_url.endswith("/v1")
    racine = moteur.base_url.removesuffix("/v1")
    with _client() as client:
        assert client.get(f"{racine}/health").status_code == 200
        assert client.get(f"{moteur.base_url}/models").status_code == 200
    assert json.loads(_contenu(moteur.base_url)) == _sortie_attendue()
    assert moteur.requetes == [CORPS]


def test_json_invalide(faux_moteur):
    moteur = faux_moteur("json_invalide")
    assert _contenu(moteur.base_url) == "pas du json"
    assert _contenu(moteur.base_url) == "pas du json"


def test_json_invalide_une_fois(faux_moteur):
    moteur = faux_moteur("json_invalide_une_fois")
    assert _contenu(moteur.base_url) == "pas du json"
    assert json.loads(_contenu(moteur.base_url)) == _sortie_attendue()


def test_references_inventees(faux_moteur):
    sortie = json.loads(_contenu(faux_moteur("references_inventees").base_url))
    assert sortie["description"] == "[adapté] Description type." + REFERENCES_INVENTEES
    assert "CWE-9999" in sortie["description"] and "CVE-2099-0001" in sortie["description"]
    assert "https://exemple.invalid/x" in sortie["description"]


def test_vecteur_invalide(faux_moteur):
    sortie = json.loads(_contenu(faux_moteur("vecteur_invalide").base_url))
    assert sortie["cvss"]["AV"] == "X"
    assert sortie["cvss"]["AC"] == "L"


def test_lent_depasse_le_delai(faux_moteur):
    moteur = faux_moteur("lent")
    with _client(timeout=0.5) as client, pytest.raises(httpx.ReadTimeout):
        client.post(f"{moteur.base_url}/chat/completions", json=CORPS)


def test_erreur_500(faux_moteur):
    moteur = faux_moteur("erreur_500")
    with _client() as client:
        assert client.get(f"{moteur.base_url}/models").status_code == 200
        reponse = client.post(f"{moteur.base_url}/chat/completions", json=CORPS)
    assert reponse.status_code == 500
    assert len(moteur.requetes) == 1


def test_injoignable(faux_moteur):
    moteur = faux_moteur("injoignable")
    assert moteur.base_url.startswith("http://127.0.0.1:")
    with _client() as client, pytest.raises(httpx.ConnectError):
        client.get(f"{moteur.base_url}/models")


def test_scenario_inconnu(faux_moteur):
    with pytest.raises(ValueError):
        faux_moteur("inexistant")


def test_deux_instances_simultanees(faux_moteur):
    premier, second = faux_moteur(), faux_moteur("json_invalide")
    assert premier.base_url != second.base_url
    assert json.loads(_contenu(premier.base_url)) == _sortie_attendue()
    assert _contenu(second.base_url) == "pas du json"
    assert len(premier.requetes) == 1 and len(second.requetes) == 1


def test_config_test(config_test, tmp_path):
    assert config_test.moteur.mode == "externe"
    assert config_test.moteur.timeout_s == 1.0
    assert config_test.moteur.base_url.startswith("http://127.0.0.1:")
    assert config_test.chemins.var == tmp_path / "var"
    assert config_test.chemins.catalogue.is_absolute()
    assert config_test.chemins.catalogue.parts[-2:] == ("donnees", "catalogue")
    with _client() as client:
        assert client.get(f"{config_test.moteur.base_url}/models").status_code == 200
