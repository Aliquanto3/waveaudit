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
)
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
            return JSONResponse(_completion(corps, json.dumps(recit, ensure_ascii=False)))
        if scenario == "references_inventees":
            sortie["description"] += REFERENCES_INVENTEES
        elif scenario == "vecteur_invalide":
            sortie["cvss"]["AV"] = "X"
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
