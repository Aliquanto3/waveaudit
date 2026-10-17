# Revue — story 10 « Pipeline fiches et prompt »

Branche `story-10-revue` (depuis `story-10`, 26c5db8, déjà à jour sur `main` 9e1faed, sans conflit). Contrat : contrats §5, §6, §8, AD-4, AD-6, AD-15, stories.yaml id 10.

## Revue

| Sévérité | Source | Constat | Décision | Motif |
|---|---|---|---|---|
| low | second avis 1 | `corps` et `actif` insérés tels quels : un `</note>` dans la note ferme la délimitation (injection de consignes) | rejeté, écart à arbitrer | reproduit par construction, mais §8 fige la forme exacte du message `user` ; vraisemblance faible (l'auditeur écrit ses notes ; les notes de démo contiennent des charges HTML, pas `</note>`) ; en aval, les garde-fous imposent références et CVSS du constat type et la fiche est relue. Échapper les balises serait un écart au §8 : à décider au contrat |
| medium | second avis 2 | Le nouvel essai rejoue les mêmes messages avec seed fixe (42) et température 0.2 : sur llama-server, sortie très probablement identique, donc essai sans effet | reporté | §5 dit « un seul nouvel essai » sans plus ; varier la seed demanderait de changer le port `Moteur.generer_json` (socle, AD-0). Vérification sur le vrai SLM (banc) : compter les seconds essais qui réussissent ; si aucun, amender §5 (seed + 1 ou message correctif) |
| low | second avis 3 | Moteur tombé en cours de lot : repli note par note, jusqu'à `timeout_s` (180 s) par note | reporté | conforme au §5 (repli immédiat par note) ; coupure du lot au-delà de N `repli_moteur` consécutifs : à arbitrer avec la story 12 (lot) |
| info | second avis 4 | Seul le premier candidat est transmis au prompt | rejeté | conforme au §5 et §8 |
| low | dev | `01-xss-reflechi` rattachée à `WEB-XSS-STOCKE` | reporté | calibrage CAP-3, story 11 |
| info | revue | `prompt.tronquer` public, absent du §8 | accepté | ajout sans effet sur `construire` ; évite de changer sa signature |

Aucune correction de code : aucun constat medium ou high réel n'est corrigeable sans sortir du contrat ou toucher au socle.

Écarts au contrat à arbitrer : échappement des balises dans `<note>` (§8) ; nature du nouvel essai (§5, seed ou message correctif, port `Moteur` du socle).

Vérifié : branchement via `REGISTRE["fiches"]` (import paresseux), catalogue lu une fois, `constat_attendu` et références absents du prompt, `note_tronquee` en tête des `motifs_initiaux`, replis aux bons motifs, 0 requête pour `non_traitee` et `non_rattachee`. Exécution sur les 20 notes de démo : nominal 20 ok / 20 requêtes ; `json_invalide` 20 `a_revoir` / 40 ; `erreur_500` 20 `a_revoir` / 20.
Complexité : 0 constat (aucune structure qui grossit ; `assembler` en une passe).
Sécurité : aucun appel réseau hors faux moteur local.
Tests : ciblés 15 verts ; suite complète 211 verts ; ruff check et format verts.
