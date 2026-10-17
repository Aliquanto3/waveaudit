# Revue — story 4 « Catalogue de constats types »

Branche `story-4-revue` (depuis `story-4`, 9f101f9, rebasée sur `main` 900e975). Contrat : contrats §3, §15, §16, stories.yaml id 4.

## Revue

| Sévérité | Source | Constat | Décision | Motif |
|---|---|---|---|---|
| medium | revue | `CatalogueYaml` sur un dossier absent renvoyait un catalogue vide sans erreur : toutes les notes auraient fini `non_rattachee` | corrigé | §15 « toute erreur lève `ConfigurationInvalide` » ; `constats()` lève, `verifier` renvoie une erreur ; test `test_constats_leve_configuration_invalide_si_dossier_absent` |
| medium | revue | Erreurs de `verifier` sur plusieurs lignes (texte brut de `ValidationError` et des erreurs YAML) | corrigé | §15 : une ligne par erreur (`fichier:id: message`) ; résumé `loc: msg` sur une ligne ; test `test_erreurs_de_verifier_tiennent_sur_une_ligne` |
| medium→low | second avis 1 | `verifier` ne contrôle ni 6 à 12 mots-clés, ni FR+EN, ni le gabarit de `source` | rejeté pour `verifier`, couvert par un test | §15 ne liste pas ces règles (ce sont des consignes de rédaction de la story) ; test `test_contenu_du_catalogue_du_depot_suit_le_cahier_des_charges` sur le catalogue du dépôt (6 à 12 mots-clés, gabarit de `source`, référence citée dans `source`, domaines autorisés) ; FR+EN relu à la main (voir 7) |
| medium→low | second avis 2 | Lien id de référence / URL non vérifié | rejeté pour `verifier`, couvert par un test | hors §15 ; le même test exige `CWE-n` → `definitions/n.html` et `A0X:2021` → `/Top10/A0X_2021-` ; le catalogue du dépôt passe |
| low | second avis 3 | Branche « au moins une référence » inatteignable | rejeté | règle §15 déjà imposée par le socle (`min_length=1`), testée par le cas de schéma invalide ; garde défensive sans coût |
| low | second avis 4 | Titres de références repris des noms CWE/OWASP | rejeté | ce sont les intitulés officiels des entrées citées (noms, pas du texte rédigé) ; descriptions, impacts et recommandations sont rédigés en propre |
| low | second avis 5 | Sévérités surévaluées | corrigé | `AD-LAPS-ABSENT` et `AD-DELEGATION-NON-CONTRAINTE` PR:H (admin local préalable) 9.0 → 8.4 ; `AD-ADMINS-EXCESSIFS` AC:H, S:U 9.0 → 7.1 (faiblesse structurelle, pas une exploitation directe) ; `INFRA-SERVICE-OBSOLETE` et `INFRA-RDP-EXPOSE` AC:H 9.8 → 8.1 (exploitation conditionnée à une faille ou à des identifiants) ; `WEB-XXE` A:L 9.1 → 8.2 |
| low | second avis 6 | CWE-521 mal rattaché | corrigé | `AD-LAPS-ABSENT` → CWE-1391 (identifiants faibles, réutilisés) ; `INFRA-SNMP-COMMUNAUTE` → CWE-1392 (identifiants par défaut) ; `source` réalignée |
| low | second avis 7 | Mots-clés sans terme anglais | corrigé | ajout de termes EN pour `CRYPTO-CERTIFICAT-INVALIDE`, `CRYPTO-HACHAGE-FAIBLE`, `AUTRE-JOURNALISATION-INSUFFISANTE`, et aussi `AD-LAPS-ABSENT`, `AD-ADMINS-EXCESSIFS` |
| low | revue | Trois titres de moins de 20 caractères (`Injection SQL`…) : le garde-fou §6 (story 3) remplace un titre de fiche plus court, d'où `a_revoir` si le modèle reprend le titre du catalogue | corrigé | titres allongés ; règle ajoutée au test de contenu |
| low | revue (complexité) | `obtenir` relisait et réanalysait tous les YAML à chaque appel (un appel par fiche), et la détection de doublons était en O(n²) | corrigé | catalogue chargé une fois par instance dans un dictionnaire ; `obtenir` en O(1) ; test `test_obtenir_ne_relit_pas_le_catalogue` |
| low | revue | URL des références non vérifiées en ligne (POC sans réseau) | reporté | à faire avec réseau : requête HEAD sur les 41 URL du catalogue, statut 200 attendu |
| low | revue | Aucune référence ANSSI alors que formats.md cite « guide ANSSI » | reporté | non bloquant (au moins une référence par constat suffit) ; ajouter des références `ANSSI-<SIGLE>` vers cyber.gouv.fr après vérification en ligne des URL |

Écart du dev (`constats()` / `obtenir(id)` au lieu de `charger()`) : accepté, c'est le port `Catalogue` de contrats §3.
Complexité : 1 constat (corrigé).
Intégration : `verifier` n'a pas encore d'appelant (`waveaudit catalogue verifier`, story CLI) ; signature `verifier(dossier) -> list[str]` conforme à la story.
Tests : ciblés 23 verts ; suite complète 106 verts ; ruff check et format verts.
