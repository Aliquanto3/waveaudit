---
id: story-6
title: Adaptateur moteur compatible OpenAI
status: review
sources:
  - ../stories.yaml
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
---

# Story 6 — Adaptateur moteur compatible OpenAI

## Livré

- `src/waveaudit/adaptateurs/moteur_openai.py` : `MoteurOpenAI` implémente le port
  `domaine.ports.Moteur` (contrats §3, AD-3) contre un endpoint compatible OpenAI
  (llama-server ou API externe) :
  - `__init__(base_url, modele_api, *, cle_api="", timeout_s=180.0, temperature=0.2, seed=42)` ;
    construit un `httpx.Client(base_url=..., trust_env=False, timeout=timeout_s, headers=...)`.
    L'en-tête `Authorization: Bearer <cle_api>` n'est posé que si `cle_api` n'est pas vide.
  - `sonder()` : `GET {base_url}/models` ; `MoteurInjoignable` si le statut diffère de 200 ou en
    cas d'erreur `httpx` (connexion refusée, timeout).
  - `generer_json(messages, schema, *, max_tokens)` : `POST {base_url}/chat/completions` avec
    `model` = `modele_api`, `messages`, `temperature`, `seed`, `max_tokens` et
    `response_format = {"type": "json_schema", "json_schema": {"name": "sortie_fiche",
    "strict": true, "schema": schema}}`. `MoteurInjoignable` sur une erreur `httpx` ou un statut
    différent de 200. `SortieInvalide` seulement si `choices[0].message.content` n'est pas du
    JSON ou n'est pas un objet ; aucune validation du schéma.
  - `fermer()` ferme le client HTTP (non appelé par cette story : aucun appelant encore, voir
    Reports).
- `tests/unitaires/test_moteur_openai.py`, uniquement contre `faux_moteur` (jamais le vrai
  modèle ni le réseau) : corps de requête nominal conforme (`model`, `messages`, `temperature`,
  `seed`, `max_tokens`, `response_format`) ; `json_invalide` → `SortieInvalide` ; `erreur_500` et
  `injoignable` → `MoteurInjoignable` (sur `generer_json` et sur `sonder`) ; `lent` avec
  `timeout_s=1.0` → `MoteurInjoignable` ; `sonder()` qui réussit en nominal ; en-tête
  `Authorization` absent si `cle_api=""`, présent (`Bearer <cle_api>`) sinon ; `trust_env=False`
  vérifié en pratique (un `HTTP_PROXY` bidon posé par `monkeypatch` ne fait pas échouer `sonder`
  contre le faux moteur local).

## Écarts au contrat (variantes minimales)

- Les tests d'en-tête `Authorization` lisent `moteur._client.headers` plutôt que de faire
  remonter l'en-tête reçu par le faux moteur : contrats §13 ne fait pas remonter les en-têtes
  HTTP dans `FauxMoteur.requetes` (seulement le corps JSON des `POST`), et ce n'est pas une
  structure du socle modifiable par cette story.

## Reports

- Aucun appelant construit encore `MoteurOpenAI` (`application/composition.py`, hors périmètre
  de cette story) : non testé en intégration, seulement via le port `Moteur` contre le faux
  moteur.

## Revue

| Sévérité | Source | Constat | Décision | Motif |
|---|---|---|---|---|

Tests : ciblés 10 verts (`test_moteur_openai.py`) ; suite complète lancée avant intégration.
