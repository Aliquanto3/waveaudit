---
id: story-D2
title: Intégration continue GitHub Actions
status: review
sources:
  - ../stories.yaml
---

# Story D2 — Intégration continue GitHub Actions

## Livré

- `.github/workflows/ci.yml` : job unique `test` sur `windows-latest`.
  - Déclencheurs : `push` sur `main` et `workflow_dispatch`.
  - `permissions: contents: read`.
  - `actions/checkout@v5`.
  - `astral-sh/setup-uv` épinglé par SHA de commit (tag `v10.3.0`, vérifié via
    `gh api repos/astral-sh/setup-uv/releases/latest` puis
    `gh api repos/astral-sh/setup-uv/git/refs/tags/v10.3.0`), avec `enable-cache: true`.
  - Étapes : `uv sync --locked`, `uv run ruff check`, `uv run ruff format --check`,
    `uv run pytest -q --tb=short -p no:warnings`.
- Pas de modification du README : le badge CI sera ajouté par la story 16 (réécriture du
  README), qui tourne en parallèle. Écart assumé par consigne d'orchestration.

## Vérifications locales (avant intégration)

- `uv sync --locked` : OK.
- `uv run ruff check` : OK (aucune erreur).
- `uv run ruff format --check` : OK (90 fichiers déjà formatés).
- `uv run pytest -q --tb=short -p no:warnings` : 250 tests passés, 1 désélectionné
  (marqueur `slow`, exclu par défaut via `addopts` de `pyproject.toml` — aucun accès au
  vrai modèle ni au réseau n'est requis par la suite par défaut).
- Pas de référence à un chemin absolu propre à cette machine ni à `theme-prive/` dans les
  tests exécutés par la CI (`tests/conftest.py`, `tests/unitaires/test_config.py`,
  `tests/unitaires/test_export_docx.py` utilisent des chemins relatifs/temporaires).
- Les tests Windows (Job Object dans `tests/unitaires/test_llama_server.py`,
  `sys._base_executable`) ne dépendent pas d'un état local : ils passent dans le run
  ci-dessus sur cette machine Windows et ne font pas d'hypothèse spécifique au poste.

## Écarts au contrat

Aucun. Le réseau sortant du seul appel `gh api` (lecture, épinglage du tag) a été utilisé
comme autorisé par la consigne d'orchestration ; aucun push, aucun déclenchement de
workflow n'a été fait depuis ce worktree.
