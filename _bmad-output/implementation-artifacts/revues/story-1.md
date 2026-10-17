# Revue — story 1 (socle, AD-0)

Commit relu : 52fb232 (base b4e0d8e). Contrat de référence : `contrats.md` de `main` (285f832).
Une passe. Les formes partagées (§1 à §5), `waveaudit.toml` (§2), le manifeste (§11, tailles et SHA-256 recoupés avec la table Stack), `addopts` (§12), le faux moteur et `config_test` (§13) et l'arborescence sont conformes.

## Revue

| Sévérité | Source | Constat | Suite |
|---|---|---|---|
| moyen | second avis 1 | Faux moteur nominal : sans `<constat>`, renvoyait une fiche plausible par défaut, masquant un prompt mal formé. | Corrigé : `content` = `SANS_CONSTAT` (non JSON), test ajouté. |
| moyen | reviewer | Script `waveaudit = cli:app` : rien n'appelle `sys.stdout.reconfigure` exigé « au début de `main()` » (§19), et `pyproject.toml` est figé après le socle. | Corrigé : `cli.main()` (reconfigure stdout/stderr puis `app()`), script `cli:main`, test qui échoue sans la reconfiguration (cp1252). |
| moyen | second avis 2 | `Ports` sans `MesureMemoire`. | Rejeté : le contrat prévoit `composition.creer_mesure_memoire()` (§9, story 12). Aucune règle n'interdit `application/banc.py` → `application/composition.py` (vérifié dans `test_architecture.py`). |
| faible | second avis 3 | `horodatage: AwareDatetime`. | Conservé : aligné sur le contrat de `main`. |
| faible | second avis 4 | `metriques_depuis_vecteur` accepte un ordre libre. | Conservé ; docstring : `vecteur(...)` recanonise, comparer pour exiger la forme canonique. |
| faible | second avis 5 | `Note.corps` vide lève `ValidationError`. | Conservé ; docstring de `Note` : l'adaptateur l'attrape et produit une `NoteInvalide`. |
| faible | second avis 6 | `charger_configuration(chemin)` relatif résolu contre `cwd`. | Corrigé : résolu contre `racine_projet()` (AD-13), test avec `chdir`. |
| faible | second avis 7 | `REGISTRE` à fabrique paresseuse. | Conservé ; `test_registre_fiches` vérifie déjà la clé et l'appelabilité sans appel. |
| faible | second avis 8 | `racine_projet` hors installation éditable. | Conservé ; message d'erreur explicite (`uv run` depuis le dépôt). |
| faible | second avis 9 | Angles morts du test d'architecture. | Corrigé en partie : règle « `adaptateurs/` n'importe ni `application`, ni `interfaces`, ni `workflows` ». Imports dynamiques (`importlib`) non couverts : rejeté, coût sans gain au POC. |
| faible | second avis 10 | `cyclonedx-bom` seulement en dev. | Corrigé : dépendance principale, `uv.lock` régénéré. |
| faible | orchestrateur | Pyright : imports inutilisés dans `test_modeles.py`. | Rejeté : le fichier est propre (`ruff` F401 vert, aucun `workflows_registre_import`) ; signalement probablement sur une version intermédiaire. |
| faible | reviewer | Le faux moteur accepte toute requête (ne vérifie ni `response_format` ni `max_tokens`). | Reporté : la story 4 (adaptateur) doit vérifier le corps envoyé via `FauxMoteur.requetes`. |
| faible | reviewer | `config_test` démarre toujours un faux moteur nominal ; un autre scénario passe par `model_copy` imbriqué (`moteur.model_copy(update={"base_url": ...})`). | Conservé : fonctionne, documenté ici pour les stories suivantes. |
| — | reviewer | Complexité : 0 constat (`FauxMoteur.requetes` en ajout O(1), aucun parcours par événement). | — |

Tests : suite complète verte, `ruff check` et `ruff format --check` propres.
