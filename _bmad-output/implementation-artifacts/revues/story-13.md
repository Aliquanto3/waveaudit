# Revue story 13 — CLI complète

Branche `story-13-revue` (depuis `story-13`, rebasée sur main dc99785 sans conflit). Constats et tri : section « Revue » de `_bmad-output/specs/spec-waveaudit-poc/stories/story-13-cli-complete.md`, reprise ci-dessous.

## Constats

Branche rebasée sur `main` (dc99785, story 14 incluse), sans conflit.

| Sévérité | Source | Constat | Suite |
|---|---|---|---|
| medium | second avis 1 | `installer` : `ConfigurationInvalide` du manifeste avalée par `except Exception` -> 4 au lieu de 2 | corrigé : traduction commune `_codes_retour` (2/3/4/5) ; test |
| medium | second avis 2 | `ui` : `--port 70000` -> trace et code 1 ; port occupé -> `sys.exit(1)` brut d'uvicorn | corrigé : `--port` borné 1..65535 (code 2), `SystemExit` non nul d'uvicorn -> code 4 ; tests |
| medium | second avis 3 | `banc` : erreurs d'`executer_banc` non traduites | corrigé : `executer_banc` sous `_codes_retour("banc")`, la story 15 n'a qu'à fournir le module ; test avec module factice |
| medium | revue | `ui` testée contre un faux `creer_app` injecté dans `sys.modules` | corrigé : test contre la vraie `creer_app`, `uvicorn.run` seul remplacé ; le port de `--port` atteint le middleware Host (200 / 400), garde actif pendant `run` |
| medium | revue | synthèse de `fiches` : `chemin_rapport.name` (« rapport.docx ») au lieu du chemin (§19), rapport introuvable sans l'id du lot | corrigé : chemin complet affiché (console locale, hors traçabilité AD-8) |
| low | second avis 4 | messages bruts en anglais avec chemins absolus (`PermissionError` de `-o`, `CalledProcessError`) | corrigé : message français « accès refusé (nom) », messages génériques passés par `_sans_chemin`, trace dans `logging` (§4) |
| low | second avis 5 | pas de test `ui` hôte non loopback, ni `--modele` en externe | partiellement rejeté : `test_ui_hote_invalide_code_2` existait déjà (0.0.0.0) ; ajouté : `--modele` externe -> `modele_api` (journal `lot_demarre`) |
| low | revue 14 | champ `erreur` du lot avec chemin absolu | sans objet pour la CLI (elle n'affiche pas ce champ) ; les messages génériques sont nettoyés par `_sans_chemin` |
| — | revue | Complexité : 0 constat (abonné en O(1) par événement, un seul comptage final) | — |

Tests : `test_cli.py` 21 verts ; suite complète 271 verts, 1 désélectionné (`slow`) ; `ruff check`
et `ruff format --check` verts.

## Écarts au contrat

Aucun nouveau. Rappel de la spec : `installer` et `sbom` sans `--config` (§19 ne le prévoit pas).
