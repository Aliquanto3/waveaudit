"""Faux moteur compatible OpenAI pour les tests (contrats §13, AD-10).

Chaque appel à `demarrer(scenario)` lance un serveur uvicorn dans un thread, sur 127.0.0.1 et
un port libre. La fixture fabrique `faux_moteur` de `conftest.py` les arrête au teardown.
"""

import asyncio
import json
import re
import socket
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from waveaudit.domaine.cvss31 import metriques_depuis_vecteur

SCENARIOS = (
    "nominal",
    "json_invalide",
    "json_invalide_une_fois",
    "references_inventees",
    "vecteur_invalide",
    "lent",
    "erreur_500",
    "injoignable",
    # [v2] contrats §13 (story de socle v2)
    "repetition",
    "langue_anglaise",
    "langue_francaise",
    "ecriture_etrangere",
    "url_de_la_note",
)
# [v2] Boucle de répétition : description (récit en incident) = REPETITION * 60, tronquée au
# maxLength de la rubrique lu dans response_format.json_schema.schema (1 200 par défaut).
REPETITION = "sans restriction d'accès, "
LONGUEUR_REPETITION_DEFAUT = 1200
# [v2] Textes fixes, au moins 3 mots-outils de leur langue (contrats §6 étape 6) par rubrique,
# sans identifiant ni URL, plus de 20 caractères, sans répétition.
TEXTE_ANGLAIS = (
    "The application does not validate the input that is sent by the user, and this allows "
    "an attacker to inject content into the page."
)
TEXTE_FRANCAIS = (
    "L'application ne valide pas les données envoyées par l'utilisateur, ce qui permet à un "
    "attaquant d'injecter du contenu dans la page."
)
ECRITURE_ETRANGERE = "経"
_RUBRIQUES_LANGUE = {
    "fiche": ("description", "impact", "recommandation"),
    "incident": ("recit", "impact", "recommandation"),
}
_NOTE = re.compile(r"<note>(.*?)</note>", re.DOTALL)
_URL = re.compile(r"https?://\S+")
_PONCTUATION_FINALE = ".,;:)]}>\"'"
REFERENCES_INVENTEES = " CWE-9999 CVE-2099-0001 https://exemple.invalid/x"
DELAI_LENT_S = 3.0
_CONSTAT = re.compile(r"<constat>(.*?)</constat>", re.DOTALL)
# Réponse non JSON si le dernier message user n'a pas de balise <constat> : un prompt mal formé
# échoue visiblement (SortieInvalide côté adaptateur) au lieu de produire une fiche plausible.
SANS_CONSTAT = "ERREUR faux moteur : balise <constat> absente"
# Mode incident (contrats §21) : balise <regle> présente, <constat> absente.
_REGLE = re.compile(r"<regle>(.*?)</regle>", re.DOTALL)
# Une technique ATT&CK, une IP et un hachage inventés, ajoutés au récit (CAP-5).
REFERENCES_INVENTEES_INCIDENT = " T9999 T1110.999 203.0.113.254 " + "0f" * 32


@dataclass
class FauxMoteur:
    base_url: str  # http://127.0.0.1:<port>/v1
    requetes: list[dict] = field(default_factory=list)  # corps JSON des POST reçus, dans l'ordre


def _port_libre() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _sortie_nominale(corps: dict) -> dict | None:
    """Sortie nominale, ou None si le dernier message user n'a pas de balise <constat>."""
    messages = [m for m in corps.get("messages", []) if m.get("role") == "user"]
    texte = messages[-1].get("content", "") if messages else ""
    trouve = _CONSTAT.search(texte)
    if trouve is None:
        return None
    constat = json.loads(trouve.group(1))
    sortie: dict = {
        rubrique: "[adapté] " + constat[rubrique]
        for rubrique in ("titre", "description", "impact", "recommandation")
    }
    sortie["cvss"] = metriques_depuis_vecteur(constat["cvss_vecteur"]).model_dump()
    return sortie


def _sortie_incident(corps: dict) -> dict | None:
    """Récit nominal du mode incident, ou None si le dernier message user n'a pas de <regle>."""
    messages = [m for m in corps.get("messages", []) if m.get("role") == "user"]
    texte = messages[-1].get("content", "") if messages else ""
    trouve = _REGLE.search(texte)
    if trouve is None:
        return None
    regle = json.loads(trouve.group(1))
    sources = {
        "titre": "titre",
        "recit": "description",
        "impact": "impact",
        "recommandation": "recommandation",
    }
    return {rubrique: "[adapté] " + regle[cle] for rubrique, cle in sources.items()}


def _dernier_user(corps: dict) -> str:
    messages = [m for m in corps.get("messages", []) if m.get("role") == "user"]
    return messages[-1].get("content", "") if messages else ""


def _longueur_max(corps: dict, rubrique: str) -> int:
    """maxLength de `rubrique` dans le schéma envoyé, sinon LONGUEUR_REPETITION_DEFAUT."""
    try:
        schema = corps["response_format"]["json_schema"]["schema"]
        return int(schema["properties"][rubrique]["maxLength"])
    except (KeyError, TypeError, ValueError):
        return LONGUEUR_REPETITION_DEFAUT


def _url_de_la_note(corps: dict) -> str | None:
    """Première URL de la balise <note> du dernier message user, ponctuation finale retirée."""
    note = _NOTE.search(_dernier_user(corps))
    url = _URL.search(note.group(1)) if note else None
    return url.group().rstrip(_PONCTUATION_FINALE) if url else None


def _appliquer_scenario_v2(scenario: str, sortie: dict, corps: dict, mode: str) -> None:
    """Scénarios v2 (contrats §13). `mode` "incident" : `recit` au lieu de `description`.

    `url_de_la_note` ne modifie rien en incident (pas de balise <note>).
    """
    principale = "description" if mode == "fiche" else "recit"
    if scenario == "repetition":
        sortie[principale] = (REPETITION * 60)[: _longueur_max(corps, principale)]
    elif scenario in ("langue_anglaise", "langue_francaise"):
        texte = TEXTE_ANGLAIS if scenario == "langue_anglaise" else TEXTE_FRANCAIS
        for rubrique in _RUBRIQUES_LANGUE[mode]:
            sortie[rubrique] = texte
    elif scenario == "ecriture_etrangere":
        sortie[principale] += ECRITURE_ETRANGERE
    elif scenario == "url_de_la_note" and mode == "fiche":
        url = _url_de_la_note(corps)
        if url is not None:
            sortie["description"] += " " + url


def _completion(corps: dict, contenu: str) -> dict:
    return {
        "id": "chatcmpl-faux",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": corps.get("model", "faux-modele"),
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": contenu},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def creer_app(scenario: str, requetes: list[dict]) -> FastAPI:
    app = FastAPI()
    compteur = {"post": 0}

    @app.get("/health")
    def sante() -> dict:
        return {"status": "ok"}

    @app.get("/v1/models")
    def modeles() -> dict:
        return {"object": "list", "data": [{"id": "faux-modele", "object": "model"}]}

    @app.post("/v1/chat/completions")
    async def completions(requete: Request) -> JSONResponse:
        corps = await requete.json()
        requetes.append(corps)
        compteur["post"] += 1
        if scenario == "erreur_500":
            return JSONResponse({"error": {"message": "erreur simulée"}}, status_code=500)
        if scenario == "json_invalide" or (
            scenario == "json_invalide_une_fois" and compteur["post"] == 1
        ):
            return JSONResponse(_completion(corps, "pas du json"))
        if scenario == "lent":
            await asyncio.sleep(DELAI_LENT_S)
        sortie = _sortie_nominale(corps)
        if sortie is None:
            recit = _sortie_incident(corps)
            if recit is None:
                return JSONResponse(_completion(corps, SANS_CONSTAT))
            # vecteur_invalide : identique à nominal (aucune clé cvss en mode incident).
            if scenario == "references_inventees":
                recit["recit"] += REFERENCES_INVENTEES_INCIDENT
            _appliquer_scenario_v2(scenario, recit, corps, "incident")
            return JSONResponse(_completion(corps, json.dumps(recit, ensure_ascii=False)))
        if scenario == "references_inventees":
            sortie["description"] += REFERENCES_INVENTEES
        elif scenario == "vecteur_invalide":
            sortie["cvss"]["AV"] = "X"
        _appliquer_scenario_v2(scenario, sortie, corps, "fiche")
        return JSONResponse(_completion(corps, json.dumps(sortie, ensure_ascii=False)))

    return app


def demarrer(scenario: str = "nominal") -> tuple[FauxMoteur, Callable[[], None]]:
    """Démarre un faux moteur ; renvoie le moteur et la fonction qui l'arrête."""
    if scenario not in SCENARIOS:
        raise ValueError(f"scénario inconnu : {scenario!r} (attendus : {', '.join(SCENARIOS)})")
    if scenario == "injoignable":
        return FauxMoteur(base_url=f"http://127.0.0.1:{_port_libre()}/v1"), lambda: None

    moteur = FauxMoteur(base_url="")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    config = uvicorn.Config(
        creer_app(scenario, moteur.requetes),
        log_level="warning",
        lifespan="off",
        timeout_graceful_shutdown=1,
    )
    serveur = uvicorn.Server(config)
    fil = threading.Thread(target=serveur.run, kwargs={"sockets": [sock]}, daemon=True)
    fil.start()
    limite = time.monotonic() + 10
    while not serveur.started:
        if not fil.is_alive() or time.monotonic() > limite:
            sock.close()
            raise RuntimeError("le faux moteur n'a pas démarré")
        time.sleep(0.01)
    moteur.base_url = f"http://127.0.0.1:{port}/v1"

    def arreter() -> None:
        serveur.should_exit = True
        fil.join(5)
        sock.close()

    return moteur, arreter
