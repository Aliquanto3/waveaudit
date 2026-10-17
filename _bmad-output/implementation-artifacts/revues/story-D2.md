# Revue story D2 — Intégration continue GitHub Actions

Branche `story-D2-revue` (depuis `story-D2`, rebasée sur `main` f71f0d8 sans conflit).
Constats et tri : section « Revue » de
`_bmad-output/specs/spec-waveaudit-poc/stories/story-d2-ci-github-actions.md`, reprise
ci-dessous.

## Constats

| Sévérité | Source | Constat | Suite |
|---|---|---|---|
| low | second avis 1 | pas de `python-version: "3.12"` dans `setup-uv` | corrigé : ajouté |
| low | second avis 2 | pas de `timeout-minutes` ni de `concurrency` | corrigé : `timeout-minutes: 20`, `concurrency` par `github.ref` avec `cancel-in-progress` |
| low | second avis 3 | `actions/checkout@v5` non épinglé par SHA | corrigé : épinglé sur `fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09` (tag `v5.1.0`, vérifié via `gh api`), `persist-credentials: false` ajouté |
| low | second avis 4 | SHA de `setup-uv` v10.3.0 à revérifier | confirmé correct (`gh api repos/astral-sh/setup-uv/git/refs/tags/v10.3.0` → `1c37ad07a6a961277cf70c0d37d6f313000f5884`), aucun changement |
| low | second avis 5 | pas de `PYTHONUTF8` | corrigé : `PYTHONUTF8: "1"` en `env` du workflow ; vérifié que `test_script_sortie_utf8` reste vert (son `subprocess.run` fixe son propre `env=` sans hériter de la variable de job) |
| low | revue | badge CI reporté à la story 16, qui ne le mentionne pas dans `stories.yaml` | reporté : signalé dans la section « Écarts au contrat » de la spec, à rappeler à l'invocation de la story 16 |
| — | revue | Complexité : 0 constat (fichier de configuration statique, rien ne grossit à l'exécution) | — |

## Corrections apportées

`.github/workflows/ci.yml` :
- `actions/checkout` épinglé par SHA (`persist-credentials: false`).
- `setup-uv` : ajout de `python-version: "3.12"`.
- Ajout de `timeout-minutes: 20` sur le job.
- Ajout d'un bloc `concurrency` (groupe par `github.ref`, `cancel-in-progress: true`).
- Ajout de `PYTHONUTF8: "1"` en `env` au niveau du workflow.

## Tests

- `uv run pytest -q --tb=line -p no:warnings` : 271 passés, 1 désélectionné (`slow`).
- `uv run ruff check` : OK.
- `uv run ruff format --check` : OK.

## Réseau

Seul appel réseau : `gh api` en lecture (vérification des SHA de `actions/checkout` et
`astral-sh/setup-uv`). Aucun push, aucun déclenchement de workflow depuis ce worktree.

## Écarts au contrat

Aucun nouveau. Le report du badge CI à la story 16 (déjà signalé par le dev) est confirmé
assumé par consigne d'orchestration, mais l'entrée `16` de `stories.yaml` ne le mentionne
pas explicitement — à rappeler lors de l'invocation de cette story pour que le badge ne
soit pas oublié.

## Verdict

Prête à intégrer.
