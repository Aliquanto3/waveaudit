---
id: story-V1
title: Validation sur le vrai moteur et compatibilité JSON
status: review
sources:
  - ../stories.yaml
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
---

# Story V1 : validation sur le vrai moteur et compatibilité JSON

## Livré

- Installation réelle par `uv run waveaudit installer --candidats` dans le `var/` du dépôt principal : 6 min 15 s, toutes les empreintes conformes.
  - `llama-server.exe` est à la racine du zip, donc `executable` reste inchangé.
- Tests slow : 2 passés sur le modèle par défaut (`test_llama_reel.py`, `test_reel.py`).
- Lots réels de 2 notes de démonstration pour les 4 modèles. Les mesures brutes et les sondes sont dans `_bmad-output/implementation-artifacts/validation-moteur.md`.
- Les 4 modèles sont validés (2/2 fiches ok chacun) après la correction de la revue.

## Contrats §22 : déclenché, implémenté

Avec `json_schema`, MiniCPM5 et Qwen3.5 rendent un `content` vide (`finish_reason = length`) : la condition « sortie vide » du §22 est remplie.

- Implémenté tel qu'écrit : `moteur.mode_json` (défaut `json_schema`) dans la configuration et `config/waveaudit.toml`, `mode_json` facultatif par entrée du manifeste (prime), `json_object` avec le schéma en texte à la fin du message système (`moteur_openai`).
- Mesuré : `json_object` ne corrige ni MiniCPM5 ni Qwen3.5 (même sortie vide). Aucune entrée du manifeste ne règle donc `mode_json`.

## Écart au §22, à entériner par Anaël

- Cause : la réflexion (« thinking ») activée par défaut dans le modèle de discussion consomme tout `max_tokens` dans `reasoning_content`.
- Correction : champ facultatif `reflexion` par entrée du manifeste. Un booléen est transmis par `moteur_openai` en `chat_template_kwargs = {"enable_thinking": <valeur>}` ; absent, le corps de la requête est inchangé.
- Réglé à `false` pour `minicpm5-1b-q4km` (repli) et `qwen3.5-0.8b-q4km`.
- Le contrat §22 (ou §11, manifeste) doit être amendé pour l'entériner.

## Reports

- **Rattachement de la note 01** : XSS réfléchi est rattaché à `WEB-XSS-STOCKE`, avec des scores BM25 très proches. Point à suivre dans le banc V2 ou dans le calibrage.
- **Workflow incident sur MiniCPM5 et Qwen3.5** : le réglage passe par le même adaptateur, mais aucun lot incident réel n'a été lancé sur ces modèles. À vérifier dans V2 ou C-suivante : `uv run waveaudit incident <dossier de démo> --modele minicpm5-1b-q4km`, récit en JSON valide.

## Vérifications

- Aucun llama-server ne restait après chaque exécution (psutil). Les runs ont tous duré moins de 10 min.
- Aucun appel réseau hors de l'installation autorisée.
- Le garde réseau est resté actif pendant les lots : commande `fiches`, inchangée.

## Revue

| Sévérité | Source | Constat | Décision |
|---|---|---|---|
| high | second avis 1 | « json_schema fonctionne avec les 4 modèles » contredit par les mesures (content vide) ; condition §22 remplie | corrigé : §22 implémenté, conclusion, titre et statut réécrits |
| medium | second avis 2 | §22 non implémenté ; json_object testé sur Qwen3.5 seulement ; repli MiniCPM5 inutilisable | corrigé : §22 implémenté, json_object mesuré sur les deux, `reflexion = false` (écart à entériner), MiniCPM5 validé |
| medium | second avis 3 | pas de trace de la suite non slow ni de ruff | corrigé : 648 passés, ruff vert, consignés dans la revue |
| medium | second avis 4 | lots contaminés par le téléchargement | corrigé : 4 lots refaits sans téléchargement concurrent |
| low | second avis 5 | sorties brutes des sondes non consignées | corrigé : tableau des sondes dans validation-moteur.md |
| low | revue | workflow incident non mesuré sur les modèles à réflexion coupée | reporté (voir Reports) |
| — | revue | Complexité : 0 constat (aucune structure qui grossit touchée) | — |
