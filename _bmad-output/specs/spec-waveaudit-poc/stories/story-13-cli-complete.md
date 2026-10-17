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
  `catalogue verifier` sur le dépôt (0) et sur un catalogue cassé (2), `ui` avec `creer_app` et
  `uvicorn.run` monkeypatchés (module inséré dans `sys.modules`, puisque `interfaces/web/app.py`
  n'est pas encore sur `main`) et un hôte invalide (2), `banc` avec son module absent (2, message
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

- `ui` appelle réellement `interfaces.web.app.creer_app` et `uvicorn.run`, mais ce module
  (branche `story-14`) n'est pas encore sur `main` : le test e2e monkeypatche l'import (faux
  module inséré dans `sys.modules`) et `uvicorn.run`. L'appel réel reste à vérifier après fusion
  des deux branches.
- Le corps réel de `banc` (appel du futur `application.banc`) n'est pas testé en e2e : le module
  n'existe pas encore (story 15). La story 15 est explicitement chargée de rebrancher `banc`
  (seule modification autorisée de `cli.py` par son `invoke_dev_with`) et devra vérifier l'appel
  réel.

## Revue

En attente (second avis puis reviewer).

Tests : ciblés verts (`test_cli.py` 16, `test_architecture.py`, `test_lot.py`) ; suite complète
254 verts, 1 sauté (`slow`) ; `ruff check` et `ruff format --check` verts.
