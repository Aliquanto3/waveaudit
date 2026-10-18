# Plan d'exécution — WaveAudit v2 (cadrage du 2026-10-18)

L'orchestrateur est une session principale neuve, ouverte après `/clear`. Elle lit seulement ce fichier et `etat-v2.md`, puis applique la boucle. Elle code peu et délègue. Base : `main` à a8541a7 ou après, v0.1.0 taguée. Poste : l'EliteBook cible, où les modèles sont déjà dans `var/`.

## Contrat à lire par chaque agent de story

- `_bmad-output/specs/spec-waveaudit-v2/SPEC.md`, `formats.md`, `mesures-qualite.md`, `ecarts-contrat.md`
- `_bmad-output/planning-artifacts/architecture/architecture-waveaudit-2026-10-17/ARCHITECTURE-SPINE.md` (AD-18 à AD-23) et `contrats.md` (normatif : sections [v2], [entériné v2], [revue <id>], §23 à §30)
- `_bmad-output/planning-artifacts/architecture/architecture-waveaudit-2026-10-17/impacts-v2.md` (fichiers et tests à réaligner)
- L'entrée de la story dans `_bmad-output/specs/spec-waveaudit-v2/stories.yaml` (`description`, `invoke_dev_with`) et son commentaire d'en-tête (collisions, pièges Windows)
- Stories W : en plus, `_bmad-output/planning-artifacts/ux/EXPERIENCE.md`, `DESIGN.md` et `mockups/prototype.html`. Les spines priment sur le prototype.

## Vagues

| Vague | Stories | dev-story | Remarque |
|---|---|---|---|
| 0 | S0 | Opus | Seule. C'est la seule story qui modifie le socle (AD-18). Puis **suite complète**. |
| 1 | Q1, Q2, R1, X1 (Sonnet) ; M1, W1 (Opus) | voir colonne | 6 en parallèle, sur des fichiers disjoints. W1 touche à la sécurité (CSRF, Host, CSP) et réaligne `test_ui.py` et `test_hors_ligne.py`. Puis **suite complète**. |
| 2 | Q3, W5 | Sonnet | En parallèle. Q3 est une story de données (50 constats traduits) ; voir les points d'arrêt. |
| 3 | Q4, L1 | Sonnet | En parallèle. Q4 garde les notes 21-28 et 30 en xfail jusqu'à la fin de la story. Puis **suite complète**. |
| 4 | B1 (Sonnet), R2 (Opus) | voir colonne | En parallèle. |
| 5 | Q5 (Opus), W2 (Sonnet) | voir colonne | En parallèle. Q5 lance de vrais bancs, en runs de moins de 10 min et avec un seul llama-server à la fois. Puis **suite complète**. |
| 6 | X2, W4 | Sonnet | En parallèle. Conflit d'adjacence possible sur `composition.py` : on le résout à l'intégration. Puis **suite complète**. |
| 7 | W3a | Opus | Seule. |
| 8 | W3b (Sonnet), puis DOC (Sonnet), puis REC | voir colonne | Après W3b : **suite complète**, puis les tests `slow`. REC se fait avec Anaël. |

Dans une vague parallèle, les dev-story partent ensemble ; chaque story suit ensuite ses étapes 2 à 4. On intègre les stories l'une après l'autre, dans l'ordre de la table. Un conflit sur un fichier partagé est un défaut de la story fautive.

## Boucle par story (appels bloquants, une passe de revue)

1. **Développement.** `agent-cost-kit:dev-story` (modèle de la table) travaille dans un worktree, à partir de `main` à jour. Le prompt donne : l'id et le titre de la story, les documents du contrat, le texte `invoke_dev_with`, et les règles suivantes.
   - Ne pas modifier les fichiers du socle AD-0 v2, sauf S0 et les exceptions nommées d'AD-18 (Q4 : `k1` et `b` ; Q5 : `role`, `repeat_penalty`, `duree_indicative_s` du manifeste). En cas de manque, s'arrêter et le signaler.
   - Réaligner tous les tests nommés par `invoke_dev_with` et `impacts-v2.md`, sans en affaiblir l'assertion. Écrire les nouveaux tests nommés.
   - Tests ciblés verts, puis `uv run ruff check` et `uv run ruff format --check`.
   - Un commit en français, sans fusion.
   - Pour un scénario du faux moteur autre que nominal : `fm = faux_moteur("<scenario>")`, puis `config = config_test.model_copy(update={"moteur": config_test.moteur.model_copy(update={"base_url": fm.base_url})})`.
   - Stories W : aucune ressource externe, CSP `default-src 'self'`, jeton CSRF sur toute écriture ; appliquer l'aide `tests/accessibilite.py` (créée par W5) aux pages de la story.
2. **Second avis.** `agent-cost-kit:second-avis` (Haiku) relit le diff de la branche.
3. **Revue.** `agent-cost-kit:reviewer` (Opus) reçoit la liste du second avis. Il corrige les constats moyens ou élevés réels et consigne la revue dans `_bmad-output/implementation-artifacts/revues/story-<id>.md`.
4. **Intégration** par la session principale :
   - fusion sans fast-forward dans `main`, puis `git log -1` ;
   - suite complète `uv run pytest -q --tb=line -p no:warnings` si la vague la prévoit, sinon les tests de la story ;
   - mise à jour de la ligne de la story dans `etat-v2.md` ;
   - si les tests sont verts, `git push origin main`. Anaël doit confirmer cette autorisation en début de session d'exécution ; sans son accord, on pousse à la fin de chaque vague après son feu vert.

## Points d'arrêt humains (done_checkpoint)

- **Q3.** Une fois Q3 intégrée, l'orchestrateur demande à Anaël de relire 10 constats traduits, tirés au hasard et listés dans `etat-v2.md`. La relecture ne bloque pas les vagues 3 et suivantes : la structure bilingue est figée et la relecture ne touche que des textes. Les corrections passent par un commit de données (dev-story Sonnet, sans changement de schéma), à faire avant Q5.
- **Q5.** L'orchestrateur s'arrête après le rebanc. Anaël choisit le modèle par défaut selon la règle de CAP-7, sur les mesures de `bilan-modeles-v2.md` (3 seeds, minimum et médiane). La valeur retenue est commitée par un dev-story court. Les stories W2 à W3b peuvent avancer pendant ce temps : elles lisent le défaut dans `modeles_installes` et ne dépendent pas de son nom.
- **REC.** Recette avec Anaël sur l'EliteBook. On suit les parcours de Camille (6 notes du banc, au moins une correction, un changement de candidat, une entrée non rattachée générée depuis le catalogue, export final et brouillon) et de Karim (démo CERT dans l'UI), au clavier, avec le thème. Si la recette est concluante : version 0.2.0 (pyproject, tag annoté, release GitHub avec notes tirées de `etat-v2.md`), après l'accord d'Anaël.

## Règles d'arrêt et de reprise

- **Story en échec deux fois** (tests rouges après la revue, ou fichier du socle à modifier) : la marquer `bloquée` dans `etat-v2.md` avec la raison, puis passer aux stories qui n'en dépendent pas. Ne jamais contourner une règle d'AD pour faire passer un test.
- **Suite complète rouge sur `main` après une vague** : lancer un dev-story de correction (Sonnet) dont le prompt nomme les tests en échec, avant la vague suivante.
- **Chaînes à surveiller.** Si S0 bloque, rien ne part. Si W1 bloque, les stories W sont suspendues, mais les stories Q, R, X, B et L continuent. Si R2 bloque, W2, X2, W3a et W3b sont suspendues.
- **Push** de `main` seulement après une story revue, intégrée et verte. Jamais de `--force`, aucune PR, aucune autre branche poussée. Aucun appel réseau sortant hors `uv sync` ; aucun téléchargement de modèle.
- **Q5 et tests `slow`.** Ce sont de vrais processus longs : commandes en tâche de fond ou découpées en runs de moins de 10 min, et jamais plus d'un llama-server à la fois. Psutil doit vérifier qu'aucun llama-server ne reste après chaque run. Les tests `slow` restent hors de la suite par défaut.
- **Écarts au contrat.** Ne modifier ni SPEC, ni spine, ni `contrats.md`. Un écart nécessaire est consigné dans `etat-v2.md`, section « Écarts à arbitrer ».
- **Contexte.** Couper la session (`/rename`, `/clear`, reprise depuis ce fichier et `etat-v2.md`) après la vague 4, puis avant REC.

## Fin d'exécution (orchestrateur)

Après la vague 8, ou quand plus aucune story n'est exécutable :
1. Suite complète, lint, tests `slow`, run CI vert (`gh run watch`), et `git log --oneline a8541a7..HEAD`.
2. Section « Bilan » dans `etat-v2.md` : stories intégrées et bloquées, mesures de `bilan-modeles-v2.md`, écarts à arbitrer, et coût (`/agent-cost-kit:mesurer-couts`).
3. Préparer REC avec Anaël. Ne créer le tag et la release qu'après son accord.
