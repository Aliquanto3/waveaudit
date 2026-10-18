import json
import re

import httpx
import pytest

from tests.faux_moteur import (
    REFERENCES_INVENTEES,
    REFERENCES_INVENTEES_INCIDENT,
    REPETITION,
    SANS_CONSTAT,
    SCENARIOS,
    TEXTE_ANGLAIS,
    TEXTE_FRANCAIS,
)

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


def test_nominal_sans_balise_constat_renvoie_du_non_json(faux_moteur):
    moteur = faux_moteur()
    corps = {"model": "m", "messages": [{"role": "user", "content": "<note>x</note>"}]}
    with _client() as client:
        reponse = client.post(f"{moteur.base_url}/chat/completions", json=corps)
    assert reponse.status_code == 200
    contenu = reponse.json()["choices"][0]["message"]["content"]
    assert contenu == SANS_CONSTAT
    with pytest.raises(json.JSONDecodeError):
        json.loads(contenu)


# --- Mode incident (contrats §21) : balise <regle>, sans <constat> ----------------------------

REGLE = {
    "id": "INC-LIN-SSH-FORCE-BRUTE",
    "titre": "Force brute SSH",
    "description": "Description type de la règle.",
    "impact": "Impact type.",
    "recommandation": "Recommandation type.",
}
CORPS_INCIDENT = {
    "model": "m",
    "messages": [
        {"role": "system", "content": "consigne"},
        {
            "role": "user",
            "content": f"<regle>{json.dumps(REGLE, ensure_ascii=False)}</regle>"
            "<preuves>2026-10-14T08:02:10+02:00 BASTION01 Failed password</preuves>",
        },
    ],
}
RECIT_NOMINAL = {
    "titre": "[adapté] Force brute SSH",
    "recit": "[adapté] Description type de la règle.",
    "impact": "[adapté] Impact type.",
    "recommandation": "[adapté] Recommandation type.",
}


def _contenu_incident(base_url: str) -> str:
    with _client() as client:
        reponse = client.post(f"{base_url}/chat/completions", json=CORPS_INCIDENT)
    assert reponse.status_code == 200
    return reponse.json()["choices"][0]["message"]["content"]


@pytest.mark.parametrize("scenario", ["nominal", "vecteur_invalide"])
def test_incident_nominal(faux_moteur, scenario):
    moteur = faux_moteur(scenario)
    sortie = json.loads(_contenu_incident(moteur.base_url))
    assert sortie == RECIT_NOMINAL
    assert "cvss" not in sortie
    assert moteur.requetes == [CORPS_INCIDENT]


def test_incident_references_inventees(faux_moteur):
    sortie = json.loads(_contenu_incident(faux_moteur("references_inventees").base_url))
    assert REFERENCES_INVENTEES_INCIDENT == " T9999 T1110.999 203.0.113.254 " + "0f" * 32
    assert sortie == RECIT_NOMINAL | {
        "recit": RECIT_NOMINAL["recit"] + REFERENCES_INVENTEES_INCIDENT
    }


def test_incident_json_invalide_une_fois(faux_moteur):
    moteur = faux_moteur("json_invalide_une_fois")
    assert _contenu_incident(moteur.base_url) == "pas du json"
    assert json.loads(_contenu_incident(moteur.base_url)) == RECIT_NOMINAL


def test_incident_constat_prioritaire_sur_regle(faux_moteur):
    """<constat> présente : mode fiches, même si une balise <regle> apparaît aussi."""
    corps = json.loads(json.dumps(CORPS))
    corps["messages"][-1]["content"] += f"<regle>{json.dumps(REGLE)}</regle>"
    with _client() as client:
        reponse = client.post(f"{faux_moteur().base_url}/chat/completions", json=corps)
    assert json.loads(reponse.json()["choices"][0]["message"]["content"]) == _sortie_attendue()


def test_sans_balise_regle_ni_constat(faux_moteur):
    corps = {"model": "m", "messages": [{"role": "user", "content": "<preuves>x</preuves>"}]}
    with _client() as client:
        reponse = client.post(f"{faux_moteur().base_url}/chat/completions", json=corps)
    assert reponse.json()["choices"][0]["message"]["content"] == SANS_CONSTAT


# --- Scénarios v2 (contrats §13 v2, story S0) : modes fiche et incident -----------------------

MOTS_EN = {"the", "of", "and", "is", "are", "to", "in", "for", "with", "that", "this", "by", "not"}
MOTS_FR = {"le", "la", "les", "un", "une", "des", "du", "de", "et", "ne", "pas", "par", "dans"}


def _poster(base_url: str, corps: dict) -> dict:
    with _client() as client:
        reponse = client.post(f"{base_url}/chat/completions", json=corps)
    assert reponse.status_code == 200
    return json.loads(reponse.json()["choices"][0]["message"]["content"])


def _avec_schema(corps: dict, rubrique: str, longueur: int) -> dict:
    copie = json.loads(json.dumps(corps))
    schema = {"type": "object", "properties": {rubrique: {"type": "string", "maxLength": longueur}}}
    copie["response_format"] = {
        "type": "json_schema",
        "json_schema": {"name": "sortie_fiche", "strict": True, "schema": schema},
    }
    return copie


def _mots(texte: str) -> list[str]:
    return [m.lower() for m in re.findall(r"(?<!\w)[^\W\d_]+(?!\w)", texte)]


def test_scenarios_v2_declares():
    for scenario in (
        "repetition",
        "langue_anglaise",
        "langue_francaise",
        "ecriture_etrangere",
        "url_de_la_note",
    ):
        assert scenario in SCENARIOS


def test_nominal_constat_anglais(faux_moteur):
    """Lot `en` : le <constat> reçu est en anglais, la sortie suit."""
    constat = CONSTAT | {
        "titre": "Reflected XSS",
        "description": "Type description.",
        "impact": "Type impact.",
        "recommandation": "Type recommendation.",
    }
    corps = json.loads(json.dumps(CORPS))
    corps["messages"][-1]["content"] = (
        f"<constat>{json.dumps(constat)}</constat><note>Asset: x\nobservations</note>"
    )
    sortie = _poster(faux_moteur().base_url, corps)
    assert sortie["titre"] == "[adapté] Reflected XSS"
    assert sortie["description"] == "[adapté] Type description."


def test_repetition_longueur_par_defaut(faux_moteur):
    sortie = json.loads(_contenu(faux_moteur("repetition").base_url))
    assert sortie["description"] == (REPETITION * 60)[:1200]
    assert len(sortie["description"]) == 1200
    assert sortie | {"description": None} == _sortie_attendue() | {"description": None}


def test_repetition_longueur_du_schema(faux_moteur):
    moteur = faux_moteur("repetition")
    sortie = _poster(moteur.base_url, _avec_schema(CORPS, "description", 300))
    assert sortie["description"] == (REPETITION * 60)[:300]


def test_repetition_incident(faux_moteur):
    moteur = faux_moteur("repetition")
    sortie = _poster(moteur.base_url, _avec_schema(CORPS_INCIDENT, "recit", 800))
    assert sortie == RECIT_NOMINAL | {"recit": (REPETITION * 60)[:800]}


def test_langue_anglaise(faux_moteur):
    sortie = json.loads(_contenu(faux_moteur("langue_anglaise").base_url))
    attendu = _sortie_attendue()
    assert sortie["titre"] == attendu["titre"] and sortie["cvss"] == attendu["cvss"]
    for rubrique in ("description", "impact", "recommandation"):
        assert sortie[rubrique] == TEXTE_ANGLAIS
    assert sum(m in MOTS_EN for m in _mots(TEXTE_ANGLAIS)) >= 3
    assert sum(m in MOTS_FR for m in _mots(TEXTE_ANGLAIS)) == 0


def test_langue_anglaise_incident(faux_moteur):
    sortie = json.loads(_contenu_incident(faux_moteur("langue_anglaise").base_url))
    assert sortie == RECIT_NOMINAL | {
        "recit": TEXTE_ANGLAIS,
        "impact": TEXTE_ANGLAIS,
        "recommandation": TEXTE_ANGLAIS,
    }


def test_langue_francaise(faux_moteur):
    sortie = json.loads(_contenu(faux_moteur("langue_francaise").base_url))
    assert sortie["titre"] == _sortie_attendue()["titre"]
    for rubrique in ("description", "impact", "recommandation"):
        assert sortie[rubrique] == TEXTE_FRANCAIS
    assert sum(m in MOTS_FR for m in _mots(TEXTE_FRANCAIS)) >= 3
    assert sum(m in MOTS_EN for m in _mots(TEXTE_FRANCAIS)) == 0


def test_langue_francaise_incident(faux_moteur):
    sortie = json.loads(_contenu_incident(faux_moteur("langue_francaise").base_url))
    assert sortie == RECIT_NOMINAL | {
        "recit": TEXTE_FRANCAIS,
        "impact": TEXTE_FRANCAIS,
        "recommandation": TEXTE_FRANCAIS,
    }


def test_ecriture_etrangere(faux_moteur):
    sortie = json.loads(_contenu(faux_moteur("ecriture_etrangere").base_url))
    assert sortie == _sortie_attendue() | {"description": "[adapté] Description type.経"}


def test_ecriture_etrangere_incident(faux_moteur):
    sortie = json.loads(_contenu_incident(faux_moteur("ecriture_etrangere").base_url))
    assert sortie == RECIT_NOMINAL | {"recit": RECIT_NOMINAL["recit"] + "経"}


def test_url_de_la_note(faux_moteur):
    corps = json.loads(json.dumps(CORPS))
    corps["messages"][-1]["content"] = corps["messages"][-1]["content"].replace(
        "observations", "voir https://app.exemple.test/login?id=1). puis https://autre.test/"
    )
    sortie = _poster(faux_moteur("url_de_la_note").base_url, corps)
    assert sortie["description"] == "[adapté] Description type. https://app.exemple.test/login?id=1"


def test_url_de_la_note_sans_url(faux_moteur):
    sortie = json.loads(_contenu(faux_moteur("url_de_la_note").base_url))
    assert sortie == _sortie_attendue()


def test_url_de_la_note_incident_sans_modification(faux_moteur):
    sortie = json.loads(_contenu_incident(faux_moteur("url_de_la_note").base_url))
    assert sortie == RECIT_NOMINAL
