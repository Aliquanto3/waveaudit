# Plan de nuit — POC WaveAudit (2026-10-17)

Orchestrateur : une session principale neuve (`/clear`), qui lit seulement ce fichier puis applique la boucle. Elle code peu et délègue.

## Contrat à lire par chaque agent de story

- `_bmad-output/specs/spec-waveaudit-poc/SPEC.md` et `formats.md`
- `_bmad-output/planning-artifacts/architecture/architecture-waveaudit-2026-10-17/ARCHITECTURE-SPINE.md`
- `_bmad-output/planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md` (normatif)
- L'entrée de la story dans `_bmad-output/specs/spec-waveaudit-poc/stories.yaml` (`description` et `invoke_dev_with`)

## Vagues

| Vague | Stories | dev-story | Remarque |
|---|---|---|---|
| 0 | 1 | Opus | Socle. Faite avant la nuit et relue par Anaël (done_checkpoint). |
| A | 2, 3, 4 | Sonnet | en parallèle |
| B | 5, 6, 7 | Sonnet | en parallèle |
| C | 8, 9 | Sonnet | en parallèle ; puis **suite complète** sur main |
| D | 10 (Opus), 11 (Sonnet) | voir colonne | en parallèle |
| E | 12 | Opus | seule ; puis **suite complète** |
| F | 13, 14 | Sonnet | en parallèle |
| G | 15 | Sonnet | après 13 (même fichier `cli.py`) |
| H | 16 | Sonnet | puis **suite complète finale** |

## Boucle par story (appels bloquants, une passe de revue)

1. `agent-cost-kit:dev-story` (modèle de la table) dans un worktree, à partir de `main` à jour. Prompt : l'id et le titre de la story, les 4 documents du contrat, le texte `invoke_dev_with`, et ces règles :
   - ne pas modifier les fichiers du socle (AD-0) ; s'arrêter et signaler en cas de manque ;
   - tests ciblés verts, puis `uv run ruff check` et `uv run ruff format --check` ;
   - un commit en français, sans fusion.
2. `agent-cost-kit:second-avis` (Haiku) sur le diff de la branche.
3. `agent-cost-kit:reviewer` (Opus) avec la liste du second avis : il corrige les constats moyens ou élevés réels et consigne la revue dans `_bmad-output/implementation-artifacts/revues/story-<id>.md`.
4. Intégration par la session principale : fusion sans fast-forward dans `main`, puis `git log -1`. Lancer `uv run pytest -q --tb=line -p no:warnings` sur `main` si la vague le prévoit, sinon les tests de la story. Mettre à jour la ligne de la story dans `etat-de-nuit.md`, puis, si les tests sont verts, `git push origin main` (autorisé par Anaël le 2026-10-17, après chaque story revue et testée).
- Dans une vague parallèle, les dev-story partent ensemble, puis chaque story suit ses étapes 2 à 4. On intègre l'une après l'autre ; un conflit sur un fichier partagé est un défaut de la story fautive.

## Règles d'arrêt et de reprise

- Si une story échoue deux fois (tests rouges après la revue, ou fichier du socle à modifier) : la marquer `bloquée` dans `etat-de-nuit.md` avec la raison et passer aux stories qui ne dépendent pas d'elle. Ne jamais contourner une règle d'AD pour faire passer un test.
- Si la suite complète est rouge sur `main` après une vague : un dev-story de correction (Sonnet) dont le prompt nomme les tests en échec, avant la vague suivante.
- Push de `main` seulement après une story revue, intégrée et verte ; jamais de `--force`, aucune PR, aucune autre branche poussée. Aucun autre appel réseau sortant hors `uv sync` ; aucun téléchargement de modèles (`installer` n'est jamais lancé la nuit).
- Ne pas modifier SPEC, spine ni `contrats.md`. Un écart nécessaire est consigné dans `etat-de-nuit.md` (section « Écarts à arbitrer »).

## État

`_bmad-output/implementation-artifacts/etat-de-nuit.md` : une ligne par story (`à faire`, `en cours`, `intégrée <sha>`, `bloquée : raison`), avec le coût si `/agent-cost-kit:mesurer-couts` est disponible en fin de nuit, et la section « Écarts à arbitrer ».

## Au réveil (Anaël)

1. Lire `etat-de-nuit.md` et les revues.
2. Sur l'EliteBook : `uv sync`, `uv run waveaudit installer --candidats`, `uv run pytest -m slow`, `uv run waveaudit banc donnees/demo/notes` pour chaque modèle.
3. Relire le catalogue (contenu rédigé par l'agent).
4. Si tout est utilisable : version 0.1.0 (pyproject, tag annoté, release GitHub) et topic `status-test`.
