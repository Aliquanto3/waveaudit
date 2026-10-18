# Revue story S0 — Socle v2

Branche `story/S0` (b3930f1, base `main` 236a2e9). Revue unique (reviewer, avec la liste du second avis).

Vérifié : conformité aux contrats §1, §2, §3, §9, §11, §13 et §25 « Formes » v2 ; AD-18 (pyproject.toml, uv.lock, conftest.py, erreurs.py, application/config.py, registre.py inchangés ; seul changement de comportement : repli qwen3.5-0.8b, plus le plafond de 64 caractères de l'id_lot imposé par §9 [revue A3]) ; branchement des noms publics (lot.py, incident.py, cli.py) ; suite complète, ruff.

## Revue

| Sévérité | Source | Constat | Décision |
|---|---|---|---|
| low | second avis 1 | `all(c.score <= 0.0 ...)` vrai sur `candidats=[]` : une entrée `fiche` sans candidat admet tout `candidat_choisi`. | Rejeté : une liste vide satisfait la définition de `non_rattachee` (aucun candidat de score > 0, cas d'un catalogue vide) ; le contrôle d'existence est à la route (§25 [revue A14]) ; durcir risquerait de refuser un lot v0.1.0 reconstruit (R2). |
| low | second avis 2 | Invariant appliqué champ par champ, plus strict que la lecture littérale. | Rejeté : aucune règle du §25 (`remplacer_fiche`, `enregistrer_resultat`, reconstruction) ne produit `fiche_generee` ou `statut_relecture` hors de l'état `fiche` ; le choix est consigné dans la story. |
| low | second avis 3 | `_NOMS_RESERVES` contient `com0` et `lpt0`. | Rejeté : Microsoft (« Naming Files, Paths, and Namespaces ») liste COM0 et LPT0 parmi les noms réservés ; refuser un nom de trop est sans risque. |
| low | second avis 4 | Installation antérieure sans qwen3.5 : en RAM basse, modèle absent tant que `waveaudit installer` n'est pas relancé. | Rejeté : `composition` lève déjà `ConfigurationInvalide("… absent : lancer `waveaudit installer`")` (composition.py l. 107-108), code 2 avec ce message. Changement admis par AD-18 ; mention dans le README à faire par DOC. |
| low | second avis 5 | README encore sur MiniCPM5 en repli. | Reporté à la story DOC (déjà dans les reports de la story). |
| low | reviewer | `test_architecture` ne voyait pas `import waveaudit.application.lot` sans alias suivi de `waveaudit.application.lot._x`. | Corrigé : nom qualifié détecté (`ast.unparse`), cas ajouté au test de l'analyseur. |
| low | reviewer | `tests/e2e/test_lot.py` fait `monkeypatch.setattr(lot, "_maintenant", …)` (nom privé passé en chaîne). | Laissé : ce n'est pas un import (règle du §9 v2) ; aucun nom public `maintenant` au contrat. |
| — | reviewer | Complexité : 0 constat (validateur d'`EtatRelecture` en O(n), aucune structure qui grossit par événement ajoutée). | — |

## Reports

- `Moteur.generer_json(seed=…)` et `Exporteur.exporter(options=…)` : protocoles en avance sur `MoteurOpenAI` et `ExportDocx` (Q1 et story d'export), sans effet à l'exécution.
- Repli qwen3.5-0.8b sur le vrai moteur non exercé ici (pas de test réel hors `slow`) : à vérifier en V1, machine à RAM basse ou `moteur.modele = "qwen3.5-0.8b-q4km"`, après `waveaudit installer`.
