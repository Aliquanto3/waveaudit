---
id: story-16
title: Preuve hors ligne, test réel et README
status: review
sources:
  - ../stories.yaml
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
---

# Story 16 — Preuve hors ligne, test réel et README

## Livré

- `tests/e2e/test_hors_ligne.py` (CAP-11, contrats §12) :
  - un lot CLI (`fiches`) complet, sous le `garde()` activé par la commande elle-même, avec
    `garde_reseau.tentatives() == []` et le garde désactivé en sortie ;
  - un lot UI complet, posté via `TestClient` à l'intérieur d'un `uvicorn.run` monkeypatché mais
    appelé depuis la commande `ui` réelle (donc sous le même `garde()` qu'en exploitation),
    même vérification ;
  - un test négatif : `application.lot.executer_lot` est remplacé par une version qui tente
    `socket.create_connection(("192.0.2.1", 80))` (TEST-NET-1, RFC 5737, jamais routée) avant
    toute autre action ; le garde lève `ConnexionInterdite` avant la connexion réelle, la CLI la
    traduit en code 4, et `tentatives()` contient bien l'adresse refusée.
- `tests/e2e/test_reel.py` (marqueur `slow`, sauté si `var/modeles` ou `llama-server` sont
  absents) : lot réel de 2 notes de démonstration, mode `local-gere` de la configuration livrée,
  via `application.lot.executer_lot` directement (il démarre et arrête lui-même `llama-server`).
  Assertions de structure seulement (champs non vides, cohérence statut/motifs, `.docx` valide,
  nombre de fiches + écartées = 2) ; `var/sorties/<id>/` et le journal du moteur sont nettoyés
  dans un `finally`, qu'il ait réussi ou non.
- `README.md` : badge CI (`.github/workflows/ci.yml`, story D2, en parallèle), prérequis,
  installation (`uv sync`, `waveaudit installer`), utilisation CLI (toutes les commandes, décrites
  d'après leur `--help` réel) et UI, preuve hors ligne (garde réseau, SHA-256, SBOM, suite de
  tests), choix et licences des modèles (tableau depuis `config/artefacts.toml`), banc (contrats
  §20, sans option inventée), limites du POC (non-goals de `SPEC.md`), bandeau de démonstration,
  mention de `theme-prive/` (ignoré par git).

## Écarts au contrat (variantes minimales)

- `test_reel.py` réutilise `var/sorties/` et `var/journaux/` du dépôt (seul endroit où les
  artefacts installés se trouvent), contrairement à la règle générale « aucun test n'écrit dans
  le `var/` du dépôt » : il nettoie ses deux chemins dans un `finally`, à l'identique de l'usage
  déjà fait par `tests/e2e/test_llama_reel.py` (story antérieure) pour son propre journal.
- Le badge CI du README pointe vers `.github/workflows/ci.yml` (story D2, développée en
  parallèle) : le lien est correct dès que ce fichier existe sur `main`, pas nécessairement au
  moment de cette story.

## Reports

- Aucun.

## Revue

Tests ciblés : `tests/e2e/test_hors_ligne.py` (3 verts) ; `tests/e2e/test_reel.py` sauté (pas de
`var/modeles` dans ce worktree), collecté sans erreur. Suite complète, `ruff check` et
`ruff format --check` : voir journal de session.
