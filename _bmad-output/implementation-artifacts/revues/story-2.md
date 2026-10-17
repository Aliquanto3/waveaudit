# Revue — story 2 (recherche BM25, AD-7, contrats §7)

Commit relu : 2f5abad (base d7a8278), branche de revue `story-2-revue` (`story-2` occupée par un autre worktree).
Une passe. Tokenisation, document pondéré (titre x3, mots-clés x3, description), IDF `ln(1 + ...)`, tri score décroissant puis id, requête sans `constat_attendu` ni `actif` : conformes. `classer` n'a pas encore d'appelant (workflow, story ultérieure) ; `config.recherche.k1/b` existent dans le socle.

## Revue

| Sévérité | Source | Constat | Suite |
|---|---|---|---|
| faible | second avis 1 | `_MOTS_VIDES` contient « été », « être » accentués, comparés après retrait des accents : entrées inertes (« ete », « etre » passaient, vérifié). | Corrigé : entrées sans accent, test qui vérifie que toute la liste est déjà normalisée. |
| moyen | second avis 2 | NFKD ne décompose pas « œ »/« æ » : « mise en œuvre », « manœuvre » donnaient « uvre », « man » (vérifié), donc aucun rapprochement avec « oeuvre ». Fréquent dans des textes FR de recommandation. | Corrigé : table de ligatures (œ→oe, æ→ae, ß→ss) avant NFKD, test. Écart mineur au texte du §7 (sur-ensemble de NFKD). |
| faible | second avis 3 | Ids en double : documents fusionnés dans le dict, IDF faussé. | Rejeté : unicité des ids garantie par la vérification du catalogue (story 4, §16). |
| faible | second avis 4 | Aucun test des mots vides accentués. | Corrigé avec le constat 1. |
| faible | reviewer | Aucun test ne vérifie une valeur BM25 exacte ; le test « accents » n'exerçait aucun accent. | Corrigé : score attendu calculé à la main (ln 2 x 7,5 / 4,359375, avec `b` actif car longueurs différentes) ; test « DÉFAUT d’accès ». |
| — | reviewer | Complexité : 0 constat. `classer` est O(N x (L + Q)) par note sur un catalogue figé (~35 constats) ; reconstruire l'index à chaque note reste négligeable. | — |

Tests : `tests/unitaires/test_recherche.py` 10 verts, suite complète 63 verts, `ruff check` et `ruff format --check` propres.
