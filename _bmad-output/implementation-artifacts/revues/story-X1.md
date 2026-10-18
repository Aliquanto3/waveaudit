# Revue story X1 — Rendu Word bilingue, modes final et brouillon

Branche `story/X1` (commit 0bc4371, base `main` db81ae3).

## Revue

| Sévérité | Source | Constat | Décision |
|---|---|---|---|
| medium | second avis 1 | `_section_fiche` écrivait en dur « Vecteur : », « Score : », « Sévérité : », « Note : », « Constat type : », donc du français dans un Word `en` (CAP-8 : « un Word aux libellés anglais »). | Corrigé : clés `vecteur`, `score`, `severite`, `note`, `constat_type` ajoutées à `LIBELLES` (en : `Vector`, `Score`, `Severity`, `Note`, `Finding template`). Les valeurs françaises restent identiques ; §27 ne l'interdit pas, le contrat n'est pas modifié. Tests `test_en_mots_inline_cvss_et_tracabilite` et `test_fr_mots_inline_inchanges`. |
| medium | second avis 2 | Les `detail` des motifs (textes produits par le domaine et les workflows, en français : `garde_fous.py`, `pipeline.py`, `lot.py`) apparaissent dans la section Statut (brouillon) et dans l'annexe d'un Word `en`. | Reporté, écart à arbitrer : les traduire demande de toucher le domaine ou le contrat (§23 ne range pas les motifs parmi les effets de la langue). L'adaptateur ne peut pas les traduire sans table de correspondance des textes libres. À trancher par Anaël : soit on accepte (motifs = traçabilité technique), soit une story ajoute des `detail` par langue. |
| low | second avis 3 | Statut brut `non_traitee` / `non_rattachee` non traduit dans l'annexe `en`. | Reporté avec le point 2 : c'est un identifiant, rendu brut en français aussi depuis la v0.1.0, comme `motif.code` (`vecteur_invalide`). Le traduire seulement en `en` mettrait un libellé hors de la table §27 ; même arbitrage que les codes de motif. |
| low | second avis 4 | `test_aucun_partiel_restant` ne couvrait que le succès. | Corrigé : `test_aucun_partiel_si_le_remplacement_echoue` fait lever `os.replace` (`PermissionError`) et vérifie que l'erreur remonte et que le dossier reste vide. |
| low | second avis 5 | Pas de nouvel essai sur `PermissionError`. | Rejeté : conforme à §27 (code 4, « fermez le document dans Word », côté CLI de X2). |
| low | second avis 6 | Mode `lot` identique à la v0.1.0 prouvé seulement par les 8 tests existants. | Vérifié, sans changement : le rendu de l'export de `main` (db81ae3) et celui de la branche, comparés paragraphe par paragraphe (style et texte), tables, en-têtes et pieds, sont identiques avec et sans annexe. |
| — | reviewer | Intégration : `lot.py` et `incident.py` appellent `exporter(rapport, chemin)` sans options (défaut `lot`, inchangé) ; `export_incident_docx.py` appelle `_bandeau_en_tete_pied(document)` (défaut `BANDEAU`). Le branchement des modes (service `exporter_lot`, CLI) relève de X2. | — |
| — | reviewer | Complexité : 0 constat (rendu linéaire en fiches et entrées ; `non_validees` est un `frozenset`, test d'appartenance O(1), un seul tri en final). | — |

## Reports

- Écart à arbitrer (points 2 et 3) : textes `detail` des motifs et codes bruts en français dans un Word `en`.
