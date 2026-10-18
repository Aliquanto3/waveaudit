# Revue — story LIB (libellés par langue des statuts et motifs dans le Word)

Base 8ec9079, commit relu 72fc86c, branche `worktree-agent-a67c1d8f9c38e867d`. Relecteur :
Opus, avec la liste du second avis (Haiku). Verdict : conforme après correctifs.

Décision de l'orchestrateur appliquée : le Word `fr` revient strictement au rendu v0.1.0
(statut brut, `code : detail`, contrats §17 et §27) ; seuls les Word `en` reçoivent les
libellés. Preuve : rendu `fr` comparé paragraphe par paragraphe (style et texte) et cellule par
cellule à celui du module de 8ec9079, 3 rapports × 3 modes, identique ; test
`test_fr_rendu_v010_code_et_detail_bruts`.

| # | Sévérité | Source | Constat | Décision |
|---|---|---|---|---|
| 1 | high | second avis 1 | `repli_moteur` et `repli_sortie_invalide` recopiaient en `en` le message d'erreur français (`moteur injoignable (…)`, `réponse du moteur : …`). | Corrigé : libellé seul en `en`. |
| 2 | medium | second avis 2 | `rubrique_completee` et `repetition` recopiaient le nom français de la rubrique. | Corrigé : `RUBRIQUES_EN` (Title, Description, Impact, Recommendation), égale à `RUBRIQUES` par test ; nom inconnu : libellé seul. |
| 3 | medium | second avis 3 | `langue` perdait la rubrique en `en`. | Corrigé : rubrique traduite, et suffixe de `motif_langue` traduit (« non-Latin script », « fr function words ») ; suffixe inconnu omis. Test lié au vrai `motif_langue`. |
| 4 | medium | second avis 4 | `note_tronquee` perdait le nombre de caractères en `en`. | Corrigé : extrait par motif exact du `detail` du pipeline (« cut at N characters ») ; test qui lit la source de `pipeline.py` pour lier les deux formats ; format inconnu : libellé seul. |
| 5 | medium | second avis 5 | Le Word `fr` changeait (libellés français à la place de `code : detail` et du statut brut), contraire à §27 et §17. | Corrigé selon la décision : tables réservées à l'anglais (`MOTIFS_EN`, `STATUTS_ECARTES_EN`), `fr` inchangé ; tests `fr` existants remis à leur texte v0.1.0 (dont `test_annexe_avec_lot_interrompu`). |
| 6 | low | second avis 6 | `export_incident_docx.py` écrit `code : detail`. | Rejeté, hors périmètre : rapport CERT français, conforme à §17. |
| 7 | low | second avis 7 | Complétude : statuts listés à la main, classement des codes non testé. | Corrigé : chaque `CodeMotif` est classé dans `DETAILS_EN` (fonction de rendu du détail) ; test d'égalité des ensembles pour `MOTIFS_EN`, `DETAILS_EN`, et `STATUTS_ECARTES_EN` contre le `Literal` de `EntreeEcartee.statut`. |
| 8 | medium | reviewer | Le test de l'implémenteur ne cherchait que 5 mots des fixtures et seulement dans l'annexe. | Corrigé : `test_en_tous_les_codes_sans_francais_ni_code_brut` (3 modes), un motif de chaque code avec son `detail` réel, dans le corps et l'annexe ; aucun mot français connu ni identifiant snake_case dans tout le document. Mutation vérifiée (recopier le détail de `repli_moteur` fait échouer le test). |
| — | — | reviewer | Intégration : `_motif_affiche` et `_statut_ecartee_affiche` ne sont appelés que par `_section_fiche` et `_annexe` ; services et CLI passent `OptionsExport.langue` (X2), inchangés. | — |
| — | — | reviewer | Complexité : 0 constat (rendu linéaire en motifs et entrées, tables en dictionnaires). | — |

## Reports

- Aucun. Écart pour `etat-v2.md` : les tables anglaises étendent `LIBELLES` hors de la table
  normative de §27 et de `formats.md` ; à reporter dans le contrat lors d'une story de contrat.
