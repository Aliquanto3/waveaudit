---
id: story-5
title: Notes brutes et jeu de démonstration
status: review
sources:
  - ../stories.yaml
  - ../formats.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
---

# Story 5 — Notes brutes et jeu de démonstration

## Livré

- `src/waveaudit/adaptateurs/notes_fichiers.py` : `NotesFichiers` implémente le port
  `domaine.ports.SourceNotes` (contrats §3, §14).
  - `lire(dossier)` sélectionne `*.md`/`*.txt` (extension insensible à la casse), sans descendre
    dans les sous-dossiers, triés par `casefold()` du nom ; `EntreeInvalide` si le dossier est
    absent ou ne contient aucune note de ce type (les autres fichiers, p. ex. `.png`, sont
    ignorés sans compter comme note).
  - Lecture en `utf-8-sig` (BOM tolérée) puis normalisation `\r\n` → `\n`. En-tête YAML reconnu
    seulement si la première ligne vaut exactement `---`, refermé par la prochaine ligne `---` ;
    sinon tout le fichier est le corps.
  - `NoteInvalide(fichier, raison)` en une ligne pour : encodage illisible, en-tête non refermé,
    YAML d'en-tête illisible, en-tête qui n'est pas un mapping, et `corps` vide après strip
    (`ValidationError` du modèle `Note`, attrapée ici, jamais propagée).
  - Tolérance : une clé d'en-tête inconnue est ignorée (log `warning`) ; une
    `severite_pressentie` hors liste devient `None` (log `warning`) sans invalider la note.
- `donnees/demo/notes/01-xss-reflechi.md` … `20-journalisation-insuffisante.md` : 20 notes
  fictives de consultant, style télégraphique, vocabulaire différent du catalogue, preuves
  textuelles fictives (`exemple.test`, `*.local`, `192.0.2.0/24`), sans jamais citer
  l'identifiant du constat ni de CWE dans le corps. `constat_attendu` distincts, pris dans la
  liste figée de contrats §16 (10 web, 3 ad, 2 infra, 2 crypto, 2 config, 1 autre), fichier
  nommé `NN-<id en minuscules sans préfixe de famille>.md`.
- `tests/donnees/notes/` : cas invalides (`corps-vide.md`, `yaml-casse.md`,
  `entete-non-mapping.md`, `severite-hors-liste.md`), `ignoree.png` (ignoré) et
  `hors-sujet.md` (21ᵉ note, recette de cuisine, sert de fixture `non_rattachee` pour une story
  ultérieure).
- `tests/unitaires/test_notes.py` : les 20 notes de démonstration (toutes valides, 20
  `constat_attendu` distincts et figés, familles minimales couvertes, aucune citation du
  constat ni de CWE, preuves fictives présentes, nommage conforme) ; sélection et tri (extension
  insensible à la casse, pas de sous-dossiers, tri `casefold`) ; chaque cas invalide listé
  ci-dessus ; tolérance (champ inconnu, sévérité hors liste, absence d'en-tête, BOM + CRLF
  générés en mémoire sous `tmp_path` pour ne pas dépendre de la normalisation de fin de ligne du
  dépôt).

## Écarts au contrat (variantes minimales)

- Le cas « BOM + CRLF valide » de `invoke_dev_with` est généré dans le test (`tmp_path`), pas
  comme fichier `tests/donnees/notes/` versionné : `.gitattributes` force `eol=lf` sur tout le
  dépôt (empreintes SHA-256 stables), donc un fichier CRLF commité serait reconverti en LF au
  checkout et ne testerait plus la tolérance visée.

## Reports

- Aucun.
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
