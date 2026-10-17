---
id: story-13
title: CLI complète
status: review
sources:
  - ../stories.yaml
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
---

# Story 13 — CLI complète

## Livré

- `interfaces/cli.py` (typer), six commandes (contrats §19) :
  - `installer [--candidats]` : `manifeste.charger` puis `installation.telechargement.installer` ;
    `EmpreinteInvalide` -> 5, `OSError` -> 4 (« erreur disque pendant l'installation »), toute
    autre exception (httpx hors ligne, HTTP, etc.) -> 4 (« téléchargement impossible »).
  - `fiches DOSSIER [-o FICHIER] [--modele NOM] [--config F]` : `charger_configuration(config)`
    d'abord, puis `with garde(config.reseau.hotes_autorises):` autour du reste (import
    d'`application.lot.executer_lot` compris, après activation du garde). Bandeau
    `Démonstration — données fictives` en première et dernière ligne, une ligne par événement de
    fiche (`[i/total] note : statut (N s)`), puis la synthèse (ok/à revoir, entrées écartées,
    nom du rapport). Codes : `EntreeInvalide`/`ConfigurationInvalide` -> 2, `MoteurInjoignable`
    -> 3, `ConnexionInterdite` -> 4, toute autre exception (dont `PermissionError` sur `-o`) -> 4.
  - `ui [--port N] [--config F]` : même ordre config/garde ; refuse (code 2) un `ui.hote` hors
    `127.0.0.1`/`::1` ; puis `uvicorn.run(interfaces.web.app.creer_app(config), host=..., port=...)`.
    Import paresseux de `creer_app` et de `uvicorn`, à l'intérieur de la commande (contrats §12) :
    la story 14 (branche `story-14`, pas encore sur `main`) fournit ce module sans lancer ni
    uvicorn ni la garde elle-même.
  - `catalogue verifier [--config F]` : `adaptateurs.catalogue_yaml.verifier(catalogue)`, une
    ligne d'erreur par défaut et code 2 si la liste n'est pas vide, sinon code 0.
  - `banc DOSSIER [--modele NOM]` : même ordre config/garde ; importe `application.banc` si le
    module existe, sinon message d'une ligne (« disponible en story 15 ») et code 2.
  - `sbom` : `installation.sbom.generer(var)` ; `OSError` et toute autre exception -> 4.
  - Aucun import d'adaptateur au niveau module (contrats §12) : chaque commande importe les
    siens dans sa fonction, après le chargement de la configuration (et, pour `fiches`/`ui`/
    `banc`, après l'activation du garde).
- `tests/e2e/test_cli.py` (`CliRunner`, faux moteur, `--config` vers un TOML écrit sous
  `tmp_path`) : lot nominal sur les 20 notes de démonstration (code 0, bandeau, 20 lignes, garde
  désactivé en sortie), dossier absent (2), moteur injoignable (3), `--modele` inconnu en
  local-gere (2), `-o` vers un dossier existant simulant un verrou Windows (4, `PermissionError`),
  `catalogue verifier` sur le dépôt (0) et sur un catalogue cassé (2), `ui` avec la vraie `creer_app` et
  `uvicorn.run` monkeypatché, un hôte invalide (2), un port hors bornes (2), un port occupé (4), `banc` avec son module absent (2, message
  et garde désactivé), `sbom` et `installer` avec
  `installation.sbom.generer`/`installation.telechargement.installer` monkeypatchés (succès,
  `EmpreinteInvalide` -> 5, `OSError`/erreur httpx -> 4). Aucun vrai téléchargement ni appel au
  vrai modèle.
- `pyproject.toml` : `per-file-ignores` pour `B008` (ruff) sur `interfaces/cli.py`, idiome typer
  des valeurs par défaut `typer.Argument(...)`/`typer.Option(...)`.

## Écarts au contrat (variantes minimales)

- `installer` et `sbom` n'ont pas d'option `--config` (absente de la liste de commandes du
  contrat §19) : ils utilisent `charger_configuration()` sans surcharge. Les tests les isolent du
  `var/` réel du dépôt en monkeypatchant la fonction qui ferait l'E/S, plutôt que par un fichier
  de configuration.
- `EmpreinteInvalide` n'est pas rattrapée dans `fiches`/`ui`/`banc` (elle ne peut pas en sortir en
  l'état du contrat) : elle tomberait sinon dans le code 4 générique plutôt que 5.

## Reports

- Le corps réel de `banc` (appel du futur `application.banc`) n'est testé qu'avec un module
  factice (traduction des erreurs en codes) : la story 15 fournit le module et vérifie l'appel réel.
- Port occupé : vérifié avec un `uvicorn.run` qui fait `sys.exit(1)` (comportement d'uvicorn) ; à
  vérifier une fois à la main (`waveaudit ui` lancé deux fois) -> code 4, message d'une ligne.

## Revue

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
