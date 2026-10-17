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

Badge CI dans le README : reporté à la story 16 par consigne d'orchestration (écart signalé,
pas silencieux). À noter : l'entrée `16` de `stories.yaml` ne mentionne pas explicitement le
badge dans son `invoke_dev_with` — à rappeler explicitement au moment d'invoquer cette story,
sinon le badge risque de ne jamais être ajouté.

## Revue

Branche `story-D2-revue` (depuis `story-D2`, rebasée sur `main` f71f0d8 sans conflit).

| Sévérité | Source | Constat | Suite |
|---|---|---|---|
| low | second avis 1 | pas de `python-version: "3.12"` dans `setup-uv` | corrigé : ajouté (fixe la version même si `requires-python` change) |
| low | second avis 2 | pas de `timeout-minutes` ni de `concurrency` | corrigé : `timeout-minutes: 20` sur le job, `concurrency` par `github.ref` avec `cancel-in-progress` |
| low | second avis 3 | `actions/checkout@v5` non épinglé par SHA | corrigé : épinglé sur `fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09` (tag `v5.1.0`, vérifié via `gh api repos/actions/checkout/git/refs/tags/v5.1.0` et la liste des tags), `persist-credentials: false` ajouté |
| low | second avis 4 | SHA de `setup-uv` v10.3.0 à revérifier | confirmé correct : `gh api repos/astral-sh/setup-uv/git/refs/tags/v10.3.0` renvoie bien `1c37ad07a6a961277cf70c0d37d6f313000f5884` — aucun changement |
| low | second avis 5 | pas de `PYTHONUTF8` | corrigé : `PYTHONUTF8: "1"` ajouté en `env` du workflow ; vérifié localement que `test_script_sortie_utf8` (`tests/unitaires/test_cli.py`) reste vert avec `PYTHONUTF8=1` dans l'environnement parent — le test construit son propre `env=` pour le sous-processus (seulement `PYTHONIOENCODING` et `SYSTEMROOT`), donc la variable de job ne l'atteint pas et ne peut pas le casser |
| low | revue | badge CI reporté à la story 16, qui ne le mentionne pas explicitement dans `stories.yaml` | reporté : signalé ci-dessus (section Écarts), à rappeler à l'invocation de la story 16 ; pas de fichier contractuel (`stories.yaml`, SPEC) modifié par cette revue |
| — | revue | Complexité : 0 constat (fichier de configuration statique, aucune structure qui grossit à l'exécution) | — |

Tests : suite complète `uv run pytest -q --tb=line -p no:warnings` → 271 passés, 1 désélectionné
(`slow`) ; `uv run ruff check` et `uv run ruff format --check` verts.

Aucun push, aucun déclenchement de workflow depuis ce worktree ; seul appel réseau : `gh api`
en lecture (vérification des SHA de `actions/checkout` et `astral-sh/setup-uv`).
