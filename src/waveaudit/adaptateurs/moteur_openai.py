"""Adaptateur moteur compatible OpenAI (contrats §3, AD-3). Seul module à faire ces appels HTTP."""

import json
from typing import Literal

import httpx

from waveaudit.domaine.erreurs import MoteurInjoignable, SortieInvalide
from waveaudit.domaine.ports import Message

ModeJson = Literal["json_schema", "json_object"]
INTRO_SCHEMA = "Schéma JSON de la réponse :"


class MoteurOpenAI:
    """Implémente le port `Moteur` contre un endpoint compatible OpenAI (llama-server ou externe).

    `base_url` se termine toujours par `/v1`. `trust_env=False` : le proxy d'entreprise éventuel
    (`HTTP_PROXY`, ...) est ignoré à l'exécution.

    `mode_json` (§22) : `json_schema` (grammaire contrainte) ou `json_object`, qui ajoute le
    schéma en texte à la fin du message système. `reflexion` (écart au §22, à entériner) :
    `None` n'envoie rien ; un booléen est transmis en `chat_template_kwargs.enable_thinking`.
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
        repeat_penalty: float = 0.0,
        mode_json: ModeJson = "json_schema",
        reflexion: bool | None = None,
    ) -> None:
        self._modele_api = modele_api
        self._mode_json = mode_json
        self._reflexion = reflexion
        self._temperature = temperature
        self._seed = seed
        self._repeat_penalty = repeat_penalty
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

    def generer_json(
        self,
        messages: list[Message],
        schema: dict,
        *,
        max_tokens: int,
        seed: int | None = None,
    ) -> dict:
        """[v2] `seed` explicite (nouvelle tentative, §5) ; `None` = seed de configuration."""
        if self._mode_json == "json_object":
            messages = _avec_schema_en_texte(messages, schema)
            format_reponse: dict = {"type": "json_object"}
        else:
            format_reponse = {
                "type": "json_schema",
                "json_schema": {"name": "sortie_fiche", "strict": True, "schema": schema},
            }
        corps: dict = {
            "model": self._modele_api,
            "messages": messages,
            "temperature": self._temperature,
            "seed": self._seed if seed is None else seed,
            "max_tokens": max_tokens,
            "response_format": format_reponse,
        }
        if self._repeat_penalty != 0.0:
            corps["repeat_penalty"] = self._repeat_penalty
        if self._reflexion is not None:
            corps["chat_template_kwargs"] = {"enable_thinking": self._reflexion}
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


def _avec_schema_en_texte(messages: list[Message], schema: dict) -> list[Message]:
    """Copie des messages, le schéma en texte à la fin du premier message système (§22)."""
    texte = f"{INTRO_SCHEMA}\n{json.dumps(schema, ensure_ascii=False)}"
    copie: list[Message] = [{"role": m["role"], "content": m["content"]} for m in messages]
    for message in copie:
        if message["role"] == "system":
            message["content"] = f"{message['content']}\n{texte}"
            return copie
    return [{"role": "system", "content": texte}, *copie]
