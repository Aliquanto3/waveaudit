# Revue — story 3 « CVSS 3.1 et garde-fous »

Branche `story-3-revue` (depuis `story-3`, ad8ac67). Contrat : contrats §6, AD-5, stories.yaml id 3.

## Revue

| Sévérité | Source | Constat | Décision | Motif |
|---|---|---|---|---|
| medium | revue | `_retirer_references_inventees` écrasait tout `\s+` en un espace : sauts de ligne, listes et paragraphes de chaque rubrique perdus, même sans référence retirée | corrigé | §6 demande de normaliser les espaces, pas de supprimer la structure ; seuls les espaces horizontaux sont réduits, les espaces autour des `\n` retirés ; test `test_sauts_de_ligne_conserves_apres_nettoyage` |
| low | second avis 1 | Texte de complétion (rubrique courte) non tronqué à `longueur_max` | corrigé | §6 étape 4 : la troncature s'applique à toute rubrique ; incohérent avec le repli, où le même texte arrive par la sortie brute et était tronqué ; test `test_texte_du_constat_tronque_a_longueur_max`. Sévérité ramenée à low : textes du catalogue < 1200 en pratique |
| low | second avis 2 | `evaluer` accepte `CVSS:3.0` et les métriques temporelles | rejeté | §6 impose `cvss.CVSS3(v)` sans contrôle supplémentaire ; `evaluer` n'est appelé que sur `vecteur(m)` ou `constat.cvss_vecteur`, dont la forme relève du vérificateur du catalogue (story 4) |
| low | second avis 3 | Sévérités `faible` et `elevee` non couvertes | corrigé | ajout de deux vecteurs FIRST (3.1 faible, 8.8 elevee) |
| low | second avis 4 | `IGNORECASE` : `a12:2021` dans la prose retiré | rejeté | `re.IGNORECASE` et le motif `A\d{2}:20\d{2}` sont imposés par §6 étape 2 |
| low | revue | Un `titre` de moins de 20 caractères (fréquent : « Injection SQL ») est remplacé par celui du constat avec `rubrique_completee`, donc fiche `a_revoir` | reporté | conforme à §6 étape 4 ; à trancher au contrat (le CERT ne remplace le titre que s'il est vide). Vérifier sur le catalogue (story 4) et le banc la part de fiches `a_revoir` pour ce seul motif |
| low | revue | Retrait d'un jeton laisse « voir . » dans la prose | rejeté | cosmétique, hors contrat |

Complexité : 0 constat (aucune structure qui grossit ; traitement linéaire par rubrique).
Intégration : `garde_fous.appliquer` n'a pas encore d'appelant (pipeline des fiches, story ultérieure) ; signature conforme à §6 et §8 (`motifs_initiaux`).
Tests : ciblés 20 verts ; suite complète 73 verts ; ruff check et format verts.
