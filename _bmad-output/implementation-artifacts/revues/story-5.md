# Revue — story 5 « Notes brutes et jeu de démonstration »

Branche `story-5-revue` (depuis `story-5`, edcfef9, rebasée sur `main` 4182016 sans conflit). Contrat : contrats §14, §16, stories.yaml id 5.

## Revue

| Sévérité | Source | Constat | Décision | Motif |
|---|---|---|---|---|
| high | revue | `hors-sujet.md` obtenait un score BM25 maximal de 7,70 (jetons `sel`, `avant`, `sont`, `puis` présents dans le catalogue, `sel` vers `CRYPTO-HACHAGE-FAIBLE`) : la note aurait été rattachée et envoyée au modèle au lieu de finir `non_rattachee` (contrats §5 étape 2, §16 ; test prévu par stories.yaml id 10) | corrigé | recette réécrite sans ces jetons (score 0) ; tests `test_note_hors_sujet_n_a_aucun_jeton_du_catalogue` et `test_les_20_notes_de_demonstration_sont_rattachables` sur le vrai catalogue |
| medium | second avis 1 | `sorted(set(champs) - _CHAMPS_CONNUS)` levait `TypeError` si une clé non str (`1:`) côtoyait une clé inconnue : toute la lecture du dossier échouait | corrigé | tri sur `repr` ; reproduit puis testé (`test_cle_non_str_et_cle_inconnue_ne_font_pas_planter_le_dossier`) |
| medium | second avis 2 | `severite in frozenset` levait `TypeError` pour une liste ou un mapping | corrigé | contrôle `isinstance(str)` d'abord ; §14 : hors liste → `None` (log) ; test paramétré (liste, mapping, entier, casse) |
| low | second avis 3 | Pas de tests 0 octet ni UTF-16 | corrigé | test `test_fichier_vide_et_utf16_sont_des_notes_invalides` (comportement déjà correct : corps vide, encodage invalide) |
| low | second avis 4 | Corpus conforme (fictif, 20 notes, familles §16) | confirmé | domaines `exemple.test`/`.local`, IP 192.0.2.0/24 seulement, aucun identifiant ni CWE dans les corps |
| low | revue (réalisme) | Banc trivial ? Non : BM25 seul classe le constat attendu 1er pour 15 notes sur 20 et dans les 3 premiers pour 19 sur 20 (`05-idor` hors top 3). Le risque est l'inverse : hormis « Burp » dans deux notes, aucun terme technique (XSS, SQL, Kerberos, SMB, TLS, RDP…) n'apparaît dans les 20 corps et la rédaction est plus en prose qu'en style télégraphique, ce qui est moins réaliste qu'une vraie note de consultant | reporté | contrat respecté (« vocabulaire différent de celui du catalogue ») ; à revoir après le premier banc sur l'EliteBook : réintroduire du jargon d'outil (nmap, hashcat, GetUserSPNs) dans quelques notes si le banc sous-estime le produit |
| low | revue | Écart du dev : BOM + CRLF généré sous `tmp_path` plutôt que versionné | accepté | `.gitattributes` force `eol=lf` ; le test en mémoire vérifie bien la tolérance visée |

Complexité : 0 constat (lecture en O(n log n) pour le tri, aucune structure qui grossit).
Intégration : `NotesFichiers` implémente `SourceNotes` ; pas encore d'appelant (composition et workflow : stories ultérieures).
Tests : ciblés 30 verts ; suite complète 152 verts ; ruff check et format verts.
