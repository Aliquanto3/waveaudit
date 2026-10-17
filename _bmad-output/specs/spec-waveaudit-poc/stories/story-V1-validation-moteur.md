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
- Lots réels de 2 notes de démonstration pour les 4 modèles. Les mesures brutes sont dans `_bmad-output/implementation-artifacts/validation-moteur.md`.
- Modèles validés : granite-4.0-1b (défaut) et qwen3-1.7b (candidat).
- Modèles non validés : minicpm5-1b (repli) et qwen3.5-0.8b (candidat). Toutes leurs fiches passent en `repli_sortie_invalide`.

## Contrats §22 : non déclenché

Une sonde brute montre que `json_schema` fonctionne avec les 4 modèles.

- MiniCPM5 et Qwen3.5 activent la réflexion par défaut. Ils épuisent `max_tokens` dans `reasoning_content` et laissent `content` vide.
- `json_object` ne change rien.
- `/no_think` ne change rien pour MiniCPM5.
- `chat_template_kwargs = {"enable_thinking": false}` règle le problème : le JSON est conforme en 9 à 11 s.

La condition de §22 n'étant pas remplie, ni `mode_json` ni aucun fichier du socle n'ont été modifiés.

## Reports

- **Couper la réflexion par modèle** : c'est la seule voie vers un MiniCPM5 et un Qwen3.5 utilisables.
  - Cela demande un amendement de contrat, hors du périmètre de §22.
  - Piste : un champ facultatif du manifeste (par exemple `desactiver_reflexion = true`), traduit par `moteur_openai` en `chat_template_kwargs = {"enable_thinking": false}`.
  - Variante côté serveur : `--reasoning-budget 0` dans `llama_server`.
  - Point critique : MiniCPM5 est le **modèle de repli**, choisi automatiquement quand la RAM est basse. En l'état, il ne produit que des fiches de repli.
- **Rattachement de la note 01** : XSS réfléchi est rattaché à `WEB-XSS-STOCKE`, avec des scores BM25 très proches. Point à suivre dans le banc V2 ou dans le calibrage.

## Vérifications

- Aucun llama-server ne restait après chaque exécution (psutil). Les runs ont tous duré moins de 10 min.
- Aucun appel réseau hors de l'installation autorisée.
- Le garde réseau est resté actif pendant les lots : commande `fiches`, inchangée.
