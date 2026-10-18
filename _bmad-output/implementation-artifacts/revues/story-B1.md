# Revue story B1 — Banc v2 (recopie, taux ok, motifs, langue)

Branche `story/B1` (commit 3432627, base `main` c7a9743).

## Revue

| Sévérité | Source | Constat | Décision |
|---|---|---|---|
| medium → low | second avis 1 | Une rubrique vide complétée par le garde-fou (`rubrique_completee`, texte du catalogue) entre dans la recopie à 1,0. | Rejeté comme défaut, consigné comme écart à arbitrer. Le contrat n'est pas muet : §29 et `mesures-qualite.md` disent « pour chaque fiche qui n'est pas un repli et chaque rubrique », et n'excluent que les replis. L'implémentation est conforme. Effet sur la décision Q5 : biais vers le haut de la recopie, donc prudent (il pénalise, sans l'avantager, un modèle qui laisse des rubriques vides, face au seuil CAP-7 < 0,6). La fiche passe aussi `a_revoir` et le motif est compté dans `motifs` : le cas reste visible. Comportement figé par `test_recopie_valeurs_exactes`. |
| low | second avis 2 | `creer_catalogue` inséré au milieu de `composition.py` (la spec disait « en fin de bloc »). | Corrigé : déplacé en fin de fichier (consigne de `stories.yaml`). |
| low | second avis 3 | `--seed` non borné : `-1` vaut « seed aléatoire » pour llama.cpp, ce qui rendrait un banc non reproductible sans le signaler. | Corrigé : `typer.Option(min=0, max=2**32-1)`, code 2 hors bornes (même plage que le `% 2**32` du nouvel essai). `Configuration.moteur.seed` (socle) n'est pas modifié. |
| low | second avis 4 | Oracle faible (« > 0,8 »), pas de test CLI de `--seed`, pas de valeur attendue pour `ok`, `a_revoir` et `motifs`. | Corrigé : `test_recopie_valeurs_exactes` (valeurs constantes, pas la formule : identique 1,0, vide 0,0, repli exclu, moyenne 0,5), `test_ok_a_revoir_motifs_repli`, `test_ok_nominal_sans_motif`, `e2e/test_cli.py::test_banc_seed_cli` (142 dans banc.json, -1 et 2**32 → code 2). |
| low | reviewer | Ligne console `ok X/N` : N = nombre de fiches, donc une note écartée (non rattachée) disparaissait du dénominateur (« ok 5/5 » au lieu de « 5/6 », lecture fausse face à CAP-7). | Corrigé : N = `total` de `lot_demarre` (notes du lot). `banc.json` inchangé (`ok`, `a_revoir` restent des comptes de fiches, §29). |
| — | reviewer | Intégration : `cli.banc` passe `seed` à `executer_banc` ; la copie de configuration atteint `MoteurOpenAI` (seed par requête) et le nouvel essai (`seed + 1`) ; la langue vient de `lot_demarre.details` ; le catalogue lu est celui de `config_banc`, le même que le lot. | — |
| — | reviewer | Complexité : 0 constat (`_recopie` linéaire en fiches × 4 rubriques ; abonné en O(1) par événement ; `Counter` en un passage). | — |

## Reports

- Écart à arbitrer (point 1) : faut-il exclure de la recopie les rubriques `rubrique_completee` ? Le contrat les inclut ; les exclure changerait la définition unique de la référence 0,93 (revue A29). À trancher avant Q5 si un modèle candidat produit souvent des rubriques vides.
- Vérification réelle reportée à Q5 : rebanc EliteBook sur 3 seeds (42, 142, 242).

Tests : suite complète 933 passés (2 `slow` désélectionnés), `ruff check` et `ruff format --check` sans erreur.
