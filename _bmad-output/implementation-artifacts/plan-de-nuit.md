# Plan de nuit — POC WaveAudit (2026-10-17)

Orchestrateur : une session principale neuve (`/clear`), qui lit seulement ce fichier puis applique la boucle. Elle code peu et délègue.

## Contrat à lire par chaque agent de story

- `_bmad-output/specs/spec-waveaudit-poc/SPEC.md` et `formats.md`
- `_bmad-output/planning-artifacts/architecture/architecture-waveaudit-2026-10-17/ARCHITECTURE-SPINE.md`
- `_bmad-output/planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md` (normatif)
- L'entrée de la story dans `_bmad-output/specs/spec-waveaudit-poc/stories.yaml` (`description` et `invoke_dev_with`)
- Stories C1 à C6 : en plus, `_bmad-output/specs/spec-waveaudit-cert/SPEC.md` et `formats-incident.md` ; leurs entrées sont dans `_bmad-output/specs/spec-waveaudit-cert/stories.yaml` ; AD-17 et contrats §21.

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
| H | 16 | Sonnet | puis **suite complète** : fin du MVP |
| I | V1 | Opus | seule ; seule story autorisée à télécharger (`installer --candidats`) |
| J | V2 | Opus | seule ; longue (bancs réels) |
| K | D1, D2 | Sonnet | en parallèle ; après intégration de D2 et push, vérifier le run CI (`gh run watch`) |
| L | D3 | Sonnet | seule (README partagé avec D2) ; puis **suite complète** |
| M | C1 | Opus | seule ; seule story CERT à modifier le code existant (AD-17) ; prérequis : stories 1 à 16 intégrées (lot, composition, export_docx, cli), V1 faite ou abandonnée |
| N | C2, C3, C4, C6a | Sonnet | en parallèle (fichiers disjoints) ; puis **suite complète** |
| O | C5 | Opus | seule ; après C2, C3, C4 et C6a |
| P | C6b | Sonnet | puis **suite complète finale** et bilan |

## Boucle par story (appels bloquants, une passe de revue)

1. `agent-cost-kit:dev-story` (modèle de la table) dans un worktree, à partir de `main` à jour. Prompt : l'id et le titre de la story, les 4 documents du contrat, le texte `invoke_dev_with`, et ces règles :
   - ne pas modifier les fichiers du socle (AD-0) ; s'arrêter et signaler en cas de manque ;
   - tests ciblés verts, puis `uv run ruff check` et `uv run ruff format --check` ;
   - un commit en français, sans fusion ;
   - pour un scénario de faux moteur autre que nominal : `fm = faux_moteur("<scenario>")`, puis `config = config_test.model_copy(update={"moteur": config_test.moteur.model_copy(update={"base_url": fm.base_url})})` ;
   - le socle est plus strict que le contrat : au moins une référence par `ConstatType` ; `Note.fichier` sans chemin ; `Note.corps` vide lève `ValidationError` (l'adaptateur la convertit en `NoteInvalide`) ; `Fiche` refuse un statut `a_revoir` qui ne correspond pas à des motifs non vides ; `EvenementLot.horodatage` doit être aware (`datetime.now().astimezone()`) ; le script CLI pointe sur `cli:main`.
2. `agent-cost-kit:second-avis` (Haiku) sur le diff de la branche.
3. `agent-cost-kit:reviewer` (Opus) avec la liste du second avis : il corrige les constats moyens ou élevés réels et consigne la revue dans `_bmad-output/implementation-artifacts/revues/story-<id>.md`.
4. Intégration par la session principale : fusion sans fast-forward dans `main`, puis `git log -1`. Lancer `uv run pytest -q --tb=line -p no:warnings` sur `main` si la vague le prévoit, sinon les tests de la story. Mettre à jour la ligne de la story dans `etat-de-nuit.md`, puis, si les tests sont verts, `git push origin main` (autorisé par Anaël le 2026-10-17, après chaque story revue et testée).
- Dans une vague parallèle, les dev-story partent ensemble, puis chaque story suit ses étapes 2 à 4. On intègre l'une après l'autre ; un conflit sur un fichier partagé est un défaut de la story fautive.

## Règles d'arrêt et de reprise

- Si une story échoue deux fois (tests rouges après la revue, ou fichier du socle à modifier) : la marquer `bloquée` dans `etat-de-nuit.md` avec la raison et passer aux stories qui ne dépendent pas d'elle. Ne jamais contourner une règle d'AD pour faire passer un test.
- Si la suite complète est rouge sur `main` après une vague : un dev-story de correction (Sonnet) dont le prompt nomme les tests en échec, avant la vague suivante.
- Push de `main` seulement après une story revue, intégrée et verte ; jamais de `--force`, aucune PR, aucune autre branche poussée. Aucun autre appel réseau sortant hors `uv sync` ; aucun téléchargement de modèles (`installer` n'est jamais lancé la nuit).
- Phases après le MVP : la vague I ne démarre que si les stories 1 à 16 sont toutes intégrées et la suite verte. Si une story du MVP est bloquée, faire quand même K et L (indépendantes du vrai moteur), puis M à P seulement si les stories 1 à 16 sont intégrées (prérequis de C1).
- V1 et V2 lancent de vrais processus longs : commandes en tâche de fond ou découpées en runs de moins de 10 min ; jamais plus d'un llama-server à la fois (attendre la fin d'une story V avant d'en lancer une autre).
- Les tests `slow` restent hors de la suite par défaut ; la suite complète n'appelle jamais le vrai moteur.
- Si un push sur `.github/workflows/` est refusé (droit `workflow` du jeton), marquer D2 `bloquée : push refusé` et continuer.
- Ne pas modifier SPEC, spine ni `contrats.md`. Un écart nécessaire est consigné dans `etat-de-nuit.md` (section « Écarts à arbitrer »).

## État

`_bmad-output/implementation-artifacts/etat-de-nuit.md` : une ligne par story (`à faire`, `en cours`, `intégrée <sha>`, `bloquée : raison`), avec le coût si `/agent-cost-kit:mesurer-couts` est disponible en fin de nuit, et la section « Écarts à arbitrer ».

## Fin de nuit (orchestrateur)

Après la vague P, ou quand plus aucune story n'est exécutable :
1. Suite complète, lint, et `git log --oneline` depuis `f1da6dd`.
2. Section « Bilan » dans `etat-de-nuit.md` : stories intégrées et bloquées, mesures clés de `bilan-modeles.md`, écarts à arbitrer, et coût (`/agent-cost-kit:mesurer-couts` s'il est disponible).
3. Ne pas créer de tag ni de release : proposer la version 0.1.0 dans le bilan.

## Au réveil (Anaël)

1. Lire `etat-de-nuit.md` et les revues.
2. Sur l'EliteBook : `uv sync`, `uv run waveaudit installer --candidats`, `uv run pytest -m slow`, `uv run waveaudit banc donnees/demo/notes` pour chaque modèle.
3. Relire le catalogue (contenu rédigé par l'agent).
4. Si tout est utilisable : version 0.1.0 (pyproject, tag annoté, release GitHub) et topic `status-test`.
