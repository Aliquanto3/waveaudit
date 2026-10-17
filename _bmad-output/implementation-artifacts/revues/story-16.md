# Revue story 16 — Preuve hors ligne, test réel et README

Branche `story-16-revue` (depuis `story-16`, rebasée sur `main` 0788e08 sans conflit).

## Revue

| Sévérité | Source | Constat | Décision |
|---|---|---|---|
| medium | reviewer | Le test négatif remplaçait `executer_lot` entier : la connexion ne venait pas d'un abonné du lot, contrairement à la story (« depuis un abonné »). Or le lot ignore les erreurs d'abonné : le code 4 annoncé n'est pas ce qui se passe pour un abonné. | Corrigé : un abonné branché sur le vrai `executer_lot` tente 192.0.2.1 sur `lot_demarre` ; on vérifie `ConnexionInterdite`, `tentatives() == [("192.0.2.1", 80)]` et la fin normale de la commande. Le cas code 4 (erreur qui remonte jusqu'à la commande) reste en second test. Mutation vérifiée : sans le contrôle du garde, les deux tests échouent. |
| medium | second avis 1 | Section « Banc » du README alors que la commande n'est pas sur la base. | Rejeté : la story 15 est intégrée avant ; la section suit §20 (banc.json, échantillonnage 0,5 s) et l'aide de `cli.py` (`banc DOSSIER [--modele NOM]`), sans option inventée. |
| low | second avis 2 | Assertion `statut == a_revoir <=> motifs` tautologique (validée par `Fiche`). | Corrigé : remplacée par la présence du bandeau dans l'en-tête de chaque section du .docx. |
| low | second avis 3 | README : « seul test_reel.py appelle le vrai moteur » faux (test_llama_reel.py). | Corrigé : les deux tests `slow` cités, exclus par défaut. |
| low | second avis 4 | « ni de compilateur » non fondé. | Rejeté : SPEC.md (Cible : « sans droits admin ni compilateur ») et forged-idea. |
| low | second avis 5 | Badge CI valide seulement après rebase. | Résolu par le rebase (ci.yml présent sur main). |
| — | reviewer | Complexité : 0 constat (`_tentatives` ne grossit qu'à chaque refus ; `tentatives()` copie, lu après la fin du lot). | — |

## Reports

- `tests/e2e/test_reel.py` (slow) non exécuté (vrai moteur interdit ici) : collecté seulement, API vérifiées par introspection (`RequeteLot`, `ResultatLot`, `Fiche`, manifeste, `_ID_LOT`). À lancer en V1 : `uv run pytest -q -m slow tests/e2e/test_reel.py` après `waveaudit installer`.

## Tests

`tests/e2e/test_hors_ligne.py` 4 passés ; suite complète 275 passés, 2 désélectionnés ; ruff check et format verts.
