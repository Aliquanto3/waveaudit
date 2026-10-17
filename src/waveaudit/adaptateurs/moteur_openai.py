"""Adaptateur moteur compatible OpenAI (contrats §3, AD-3). Seul module à faire ces appels HTTP."""

import json

import httpx

from waveaudit.domaine.erreurs import MoteurInjoignable, SortieInvalide
from waveaudit.domaine.ports import Message


class MoteurOpenAI:
    """Implémente le port `Moteur` contre un endpoint compatible OpenAI (llama-server ou externe).

    `base_url` se termine toujours par `/v1`. `trust_env=False` : le proxy d'entreprise éventuel
    (`HTTP_PROXY`, ...) est ignoré à l'exécution.
    """

    def __init__(
        self,
        base_url: str,
        modele_api: str,
        *,
        cle_api: str = "",
        timeout_s: float = 180.0,
        temperature: float = 0.2,
        seed: int = 42,
    ) -> None:
        self._modele_api = modele_api
        self._temperature = temperature
        self._seed = seed
        en_tetes = {"Authorization": f"Bearer {cle_api}"} if cle_api else {}
        self._client = httpx.Client(
            base_url=base_url, trust_env=False, timeout=timeout_s, headers=en_tetes
        )

    def fermer(self) -> None:
        self._client.close()

    def sonder(self) -> None:
        reponse = self._requeter("GET", "/models")
        if reponse.status_code != 200:
            raise MoteurInjoignable(f"statut {reponse.status_code} sur /models")

    def generer_json(self, messages: list[Message], schema: dict, *, max_tokens: int) -> dict:
        corps = {
            "model": self._modele_api,
            "messages": messages,
            "temperature": self._temperature,
            "seed": self._seed,
            "max_tokens": max_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "sortie_fiche", "strict": True, "schema": schema},
            },
        }
        reponse = self._requeter("POST", "/chat/completions", json=corps)
        if reponse.status_code != 200:
            raise MoteurInjoignable(f"statut {reponse.status_code} sur /chat/completions")
        try:
            contenu = reponse.json()["choices"][0]["message"]["content"]
        except (ValueError, LookupError, TypeError) as erreur:
            # Statut 200 mais enveloppe non conforme à l'API : l'endpoint n'est pas utilisable.
            raise MoteurInjoignable("réponse du moteur non conforme à l'API") from erreur
        if not isinstance(contenu, str):
            raise SortieInvalide("réponse du moteur : contenu absent ou non textuel")
        try:
            sortie = json.loads(contenu)
        except json.JSONDecodeError as erreur:
            raise SortieInvalide("réponse du moteur : contenu non JSON") from erreur
        if not isinstance(sortie, dict):
            raise SortieInvalide("réponse du moteur : contenu JSON qui n'est pas un objet")
        return sortie

    def _requeter(self, methode: str, chemin: str, **kwargs: object) -> httpx.Response:
        try:
            return self._client.request(methode, chemin, **kwargs)
        except httpx.HTTPError as erreur:
            raise MoteurInjoignable(f"moteur injoignable ({erreur})") from erreur
