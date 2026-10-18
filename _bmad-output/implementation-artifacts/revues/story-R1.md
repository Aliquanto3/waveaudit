# Revue story R1 — Règles pures de relecture

Branche `story/R1` (b65c1f4, base `main` db81ae3). Revue unique (reviewer, avec la liste du second avis).

Vérifié : conformité au §25 « Règles pures » (codes de refus et leur ordre, E17, E29, E30, A16, A17), formes S0 inchangées, CVSS par `cvss31.evaluer` seul (sondé sur 12 vecteurs atypiques : toute erreur est une `EntreeInvalide`), aucun appelant hors tests (R2 et W3a viendront), suite complète, ruff.

## Revue

| Sévérité | Source | Constat | Décision |
|---|---|---|---|
| medium | second avis 1 | `remplacer_fiche` par `model_copy` ne revalide pas : `remplacer_fiche(e, FICHE, "WEB-999")` sur une entrée à candidats de score > 0 produit une entrée que `model_validate` refuse, donc un `relecture.json` illisible une fois persisté. La story justifiait `model_copy` par le cas A14, à tort : le validateur S0 admet déjà ce cas (tous les scores nuls). | Corrigé : copie revalidée (`_maj`) dans `corriger`, `valider` et `remplacer_fiche` ; dans `remplacer_fiche`, l'échec devient `RefusRelecture("candidat_inconnu")`. Tests : refus hors candidats, et `non_rattachee` → id du catalogue admis avec aller-retour JSON. |
| medium | second avis 2 | Correction identique sur une entrée `validee` la repassait à `a_valider`, contre « une correction identique ne change rien ». | Corrigé : comparaison sans condition de statut ; une correction égale à la fiche générée (sans correction stockée) ne change rien non plus. Tests ajoutés (échouaient sur b65c1f4). |
| medium | second avis 3 | Test d'identité vacueux ; partage R1/R2 de « pas d'incrément ». | Corrigé en partie : le test vérifie `is` (entrée renvoyée telle quelle). Le partage est conforme : `version + 1` est fait par `modifier` (R2), pas par les règles. Consigne R2 ci-dessous ; écart de texte à arbitrer : le §25 `modifier` dit « `operation(entree)` et `version + 1` » sans l'exception de la correction identique. |
| low | second avis 4 | Vecteur invalide dans `corriger` → `cvss=None` non testé. | Corrigé : test (saisie conservée, `cvss=None`, `fiche_courante` montre le CVSS généré). |
| low | second avis 5 | `all([])` vrai : fiche sans candidats admet tout `candidat_choisi`. | Rejeté : déjà jugé voulu en revue S0 (liste vide = `non_rattachee`) ; forme S0 hors périmètre. |
| low | reviewer | `cvss31.evaluer` accepte `CVSS:3.0/…` et les métriques temporelles (`/E:X`) : un vecteur corrigé non conforme au format du catalogue (§1, 8 métriques de base) est validable. | Reporté : comportement de la story 3, imposé par le contrat (« `cvss31.evaluer(cvss_vecteur)` ») ; à arbitrer (utiliser `analyser` + `evaluer` dans `corriger` ?). |
| — | reviewer | Complexité : 0 constat (`rapport_export` en O(n log n) par export, aucune structure qui grossit par événement). | — |

## Consigne pour R2

- `modifier` ne réécrit pas et n'incrémente pas `version` quand `operation(entree) == entree` (`corriger` renvoie alors l'entrée reçue).
- `demarrer_regeneration` reste responsable de `candidat_inconnu` (y compris l'existence dans le catalogue pour `non_rattachee`) ; `remplacer_fiche` ne lève `candidat_inconnu` qu'en filet de sécurité.
