---
id: story-1
title: Socle commun (AD-0)
status: review
sources:
  - ../stories.yaml
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
---

# Story 1 — Socle commun (AD-0)

## Livré

- `pyproject.toml` (package `src/waveaudit`, script `waveaudit`, Python `==3.12.*`, dépendances de la table Stack épinglées, groupe dev, `addopts = "-m 'not slow' --allow-hosts=127.0.0.1,::1"`, marqueur `slow`, ruff) et `uv.lock`.
- Arborescence de la Structural Seed avec ses `__init__.py` ; `donnees/catalogue/`, `donnees/demo/notes/` et `tests/donnees/notes/` réservés par un `.gitkeep`.
- Domaine : `modeles.py` (§1 et `schema_sortie`), `ports.py` (§3), `erreurs.py` (§4), `configuration.py` (§2), `cvss31.py` (`vecteur`, `metriques_depuis_vecteur` ; `evaluer` en story 3).
- `application/config.py` (`racine_projet`, `charger_configuration`) ; `config/waveaudit.toml` et `config/artefacts.toml` (5 artefacts, tailles et SHA-256 de la table Stack).
- `workflows/registre.py` : protocole `Workflow` et `REGISTRE["fiches"]` par import paresseux de `workflows.fiches.pipeline.creer` (story 10).
- `interfaces/cli.py` : app typer avec la seule commande `version`.
- Tests : `conftest.py` (fixtures `faux_moteur` et `config_test`), `faux_moteur.py` (8 scénarios), `test_architecture.py` (AD-1 par `ast`), `test_modeles.py`, `test_config.py`, `test_faux_moteur.py`.

## Écarts au contrat (variantes minimales)

- `EvenementLot.horodatage` est typé `AwareDatetime` (pydantic) : un datetime sans fuseau est refusé.
- Règles ajoutées sans changer les formes : `ConstatType.references` au moins 1, `Note.corps` non vide après strip, `Note.fichier` sans séparateur de chemin, `Fiche` refusée si `statut == a_revoir` ne correspond pas à `motifs` non vide.
- `config_test` pointe aussi `chemins.theme_prive` vers un dossier absent de `tmp_path`, pour que les tests d'export restent sur le thème générique même si un `theme-prive/` existe localement. Elle part des défauts du dépôt, jamais de `waveaudit.local.toml`.
- Sans balise `<constat>` dans le dernier message `user`, le faux moteur répond un `content` non JSON (`SANS_CONSTAT`) : un prompt mal formé échoue visiblement.
- Script `waveaudit = "waveaudit.interfaces.cli:main"` (et non `:app`) : `main()` reconfigure la console en UTF-8 (contrats §19) puis lance `app`.
- `cyclonedx-bom` est une dépendance principale (la commande `sbom` en a besoin à l'exécution).

## Reports

- Aucun.

## Revue

Détail : `_bmad-output/implementation-artifacts/revues/story-1.md`. 2 moyens corrigés (faux moteur sans `<constat>`, script `cli:main`), 1 moyen rejeté (`MesureMemoire` par la composition), faibles : 3 corrigés, 1 reporté (story 4 vérifie le corps de requête), les autres conservés avec docstring. Complexité : 0 constat.
