# Revue story Q4 — Index BM25 bilingue et rattachement des notes 01 et 29

Branche `story/Q4` (commit 1a02a6a, base `main` 4eb9592). Contrat : stories.yaml Q4, SPEC
CAP-5, mesures-qualite.md, contrats §7 v2, §16 et §29, impacts-v2.md lignes 15 et 17.

Verdict : intégrable ; un écart à arbitrer par Anaël (mots-clés tirés des notes 01 et 29).

## Revue

| Sévérité | Source | Constat | Décision |
|---|---|---|---|
| élevé → medium | second avis 1 | Les mots-clés ajoutés reprennent le vocabulaire des notes 01 et 29 (mesure de recouvrement des jetons à la revue : « navigateur jetable » 2/2 jetons dans la note 01 ; « erreur 500 avec trace du moteur » 4/4, « accolades doubles évaluées » 2/3 propres à la 29, « expression arithmétique dans un champ » 3/3). | Rejeté comme violation du protocole de CAP-5 : la 29 est la cible du réglage et la 01 est dans 01-20 (arbitrage de l'orchestrateur, confirmé par mesures-qualite.md l. 18). Reporté comme écart à arbitrer par Anaël : contrats §16 veut les notes de démo à un « vocabulaire différent de celui du catalogue », et la revue de la story 11 avait remplacé pour ce motif 9 mots-clés recopiés des notes par des termes génériques (règle 6 à 12 mots-clés génériques FR/EN, stories 4 et D1). Les rangs 1 de la 01 et de la 29 sont donc mesurés en échantillon. Mots-clés non modifiés dans cette revue : le verrou des notes non vues est levé, et un nouveau réglage est exclu par le protocole. |
| medium | second avis 2 | Rien ne prouve que les notes 21-28 et 30 n'ont pas été lues pendant le réglage. | Vérifié en partie, reporté : un seul commit, sans historique intermédiaire ; les scripts `diag_q4*.py` étaient déjà absents du worktree. Aucun des six mots ajoutés ne recouvre une note non vue au-delà d'un jeton générique (« navigateur » dans 23 et 30, « erreur » ou « moteur » ailleurs) ; tous viennent des notes 01 et 29. Le message du commit dit « xfail retiré sans nouvel essai après la mesure initiale » : il ne précise pas si cette mesure initiale a lu les notes non vues avant les essais. Pas prouvable après coup. |
| medium | second avis 3 | Le message de 1a02a6a fige les valeurs finales mais pas les essais et leur score sur 01-20 (mesures-qualite.md l. 35 ; le docstring du test y renvoyait). | Corrigé dans la limite du possible : essais A (base), B (index bilingue seul) et C (livré) reconstitués sur 01-20 et 29 seulement, consignés dans `bilan-modeles.md` (section v2) ; docstring de `test_rattachement_demo.py` renvoyé au bilan et réaligné (le test des notes non vues est bloquant). Le message de commit ne peut pas être réécrit sans réécrire l'historique. |
| low | second avis 4 | Un seul test bilingue (en.titre) ; rien sur en=None ni sur le poids de en.description. | Corrigé : `test_index_bilingue_ponderations_calculees_a_la_main` (scores BM25 calculés à la main pour en.titre ×3, en.description ×1, constat voisin en=None, en.impact et en.recommandation non indexés). Le cas en=None seul reste couvert par `test_score_bm25_valeur_calculee_a_la_main` (avgdl 8 inchangé). |
| low | second avis 5 | Pas de spec de story Q4. | Corrigé : ce fichier. |
| low | reviewer | Retrait de « cross-site scripting » et « reflected xss » de `WEB-XSS-REFLECHI` : il reste un seul mot-clé anglais (« burp repeater ») alors que formats.md dit que les mots-clés couvrent déjà les deux langues. | Laissé : compensé par l'index bilingue (`en.titre` « Reflected script injection (reflected XSS) ») ; modification des mots-clés exclue dans cette revue. |
| — | reviewer | Intégration : `pipeline.py` appelle `classer` sans changement de signature ; `k1`/`b` et `config/waveaudit.toml` inchangés ; pondérations restées constantes du module. | — |
| — | reviewer | Complexité : 0 constat (index reconstruit à chaque `classer`, comme avant ; aucune structure qui grossit). | — |

## Reports

- Écart à arbitrer : mots-clés tirés du vocabulaire des notes 01 et 29 (contrats §16).
- Lecture des notes non vues pendant le réglage : non prouvable après coup.
