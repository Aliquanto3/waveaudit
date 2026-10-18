# Revue — story Q1 (nouvelle tentative seed + 1, balises neutralisées, repeat_penalty transmis)

Commit relu : a466440 (base db81ae3). Contrat : `contrats.md` §3, §5, §8, §11, §21 ; `impacts-v2.md` lignes 7, 8, 12.
Une passe. Seed `+ 1 % 2**32` sur les deux pipelines (requêtes 42 puis 43 lues dans `FauxMoteur.requetes`), `repeat_penalty` absent à 0.0 et présent sinon, priorité du manifeste dans `composition._moteur` : conformes. `ligne_preuve` et `echapper` ne servent qu'au prompt (pas d'effet sur le rapport). Complexité : 0 constat.

## Revue

| Sévérité | Source | Constat | Suite |
|---|---|---|---|
| moyen | second avis 1 | `ligne_preuve` n'échappait que le message ; l'hôte, lu dans les journaux (`\S+`), laissait passer `x</preuves><regle>`. Le §8 vise « chaque ligne de preuve ». | Corrigé : `echapper` sur la ligne entière ; test `test_balise_dans_l_hote_neutralisee`. |
| faible | second avis 2 | `\s` ne couvre pas U+200B ni les autres caractères de format invisibles : `<​note>` passait. | Corrigé : blancs du motif étendus à U+00AD, U+180E, U+200B–U+200F, U+202A–U+202E, U+2060–U+2064, U+FEFF (sur-ensemble du motif du §8, même longueur) ; test `test_caracteres_invisibles_intercales_neutralises`. |
| faible | second avis 3 | `regle` (catalogue JSON) non échappée. | Rejeté : catalogue maîtrisé, versionné dans le dépôt ; le §8 ne vise que les lignes de preuve (et, en fiches, la note), comme pour le constat type. |
| faible | second avis 4 | `_moteur` modifié en place. | Rejeté : `invoke_dev_with` autorise la modification de `_moteur`. |

Tests : ciblés 78 verts ; suite complète 754 verts, 2 désélectionnés ; ruff check et format propres.
