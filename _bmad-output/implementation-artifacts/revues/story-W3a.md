# Revue — story W3a (API de relecture, régénération et export)

Commit relu : 87f8d25 (base 50caba8), branche `worktree-agent-a63c98e4ed2f64674`. ARR en
parallèle (`moteur_demande.py`, `llama_server.py`, `app.py`) et LIB intégrée sur
`export_docx.py` : non touchés. Seul `routeurs/relecture.py` change, avec ses tests.
Verdict : conforme à §24 à §27 et §30 (ordre des refus, verrou d'abord sur `candidat`,
`liberer` en `finally`, CVSS recalculé par le domaine, aucun GET n'écrit, export en POST). Ni
high ni medium ; quatre défauts faibles corrigés.

| Sévérité | Source | Constat | Décision |
|---|---|---|---|
| faible | second avis 1 | `json.loads` lève `RecursionError` (pas `ValueError`) sur un JSON très imbriqué ; 50 000 `[` passent sous la limite de 256 Kio → 500. | Corrigé dans `_corps` (422 `corps_invalide`) et `exporter` (422 `type_invalide`). Test `e2e::test_json_trop_imbrique_refus_code`. |
| faible | second avis 2 | `_charger` ne rattrapait que `ValueError` : `PermissionError` à la lecture de `relecture.json` → 500 sur les GET et avant les écritures. | Corrigé : `OSError` → 409 `relecture_illisible` (rien n'est écrit). Un `OSError` levé sous le verrou par `modifier` reste 503 `ecriture_impossible` (passager, à retenter). Test `e2e::test_relecture_verrouillee_en_lecture_409` (verrou unique libéré). |
| faible | second avis 3 | `chemin.read_bytes()` du docx hors `try` : Word ouvert entre l'écriture et la relecture → 500. | Corrigé : `PermissionError` → 409 `export_verrouille`. Test `e2e::test_docx_verrouille_a_la_relecture_409`. |
| faible | second avis 4 | Lot v0.1.0 sans `lot_demarre` (`modele=""`) en local-gere : `regenerer` passe `None` (modèle par défaut) mais la route refusait 422 « Le modèle « » ». | Corrigé : modèle `None` disponible dès qu'un modèle est installé (repli de `choisir_modele`) ; message « par défaut » sinon. Test `e2e::test_lot_sans_modele_consigne_regenerable_sur_le_modele_par_defaut`. |
| faible | second avis 5 | `_refuser_si_externe` contrôle puis écrit hors verrou inter-processus. | Rejeté : la CLI ne reprend jamais un lot existant (nouvel id à chaque lot), donc seul un lot neuf peut être écrit par un autre processus ; ses entrées restent `attente` (refus `non_modifiable` du domaine) jusqu'à `enregistrer_resultat`, déjà après `lot_demarre`, donc lot vu `en_cours`. Précision : le verrou de R2 est un `threading.Lock` par processus, pas un verrou de fichier (la spec de la story le disait à tort) ; le contrôle de version ne protège pas d'une écriture d'un autre processus entre lecture et `os.replace`. Fenêtre jugée nulle en pratique. |
| — | dev (écart) | `relecture_illisible` en 409, hors table §26. | Accepté : arbitrage d'Anaël sur R2 ; à ajouter à la table §26 (lectures, écritures, export). |
| — | dev (écart) | `index` ajouté dans `occupation` du 409 `lot_en_cours`. | Accepté : additif, `null` hors régénération ; utile à W3b pour nommer l'entrée occupée. |
| — | dev (écart) | Correction et validation permises pendant un lot de ce processus. | Accepté : §26 ne liste que `lot_en_cours_externe` ; les écritures sont sérialisées avec `enregistrer_resultat` par le verrou de processus, et le domaine refuse toute entrée non `fiche`. |
| — | dev (écart) | `generation_en_cours` inatteignable sur `POST …/candidat`. | Accepté : verrou pris d'abord (arbitrage R2). |
| — | reviewer | Complexité : 1 constat. `GET /lots/{id}/relecture` relit `relecture.json` et tout le journal (`etat_lot`) à chaque sondage : O(n) par appel, O(n²) sur un lot sondé par W3b. `GET …/entrees/{i}` relit aussi le catalogue. | Laissé : même motif que §30 (« relu à chaque appel »), au plus 100 notes ; cache du catalogue reporté (spec, Reports) si W3b sonde le détail. |

Vérifié conforme : 404 avant toute lecture, index hors `1..n` → 404 ; `conflit_version`
renvoie l'entrée à jour ; refus du domaine avant le verrou libèrent celui-ci (aucune fuite,
`finally` couvre `start()`) ; export traduit `lot_en_cours` en `lot_en_cours_externe` quand
l'occupation ne porte pas le lot ; aucun chemin absolu dans les messages ; aucun appel réseau.

Tests : ciblés 33 verts (`e2e/test_relecture_ui.py`, `e2e/test_hors_ligne.py`), les quatre
nouveaux échouent sur 87f8d25 ; `tests/e2e` et `tests/unitaires` 1055 verts ; ruff check et
format propres.

## Interfaces et consignes pour la suite

- **W3b** : contrat JSON inchangé (table de la spec de la story). Codes supplémentaires
  possibles, déjà listés : 409 `relecture_illisible` sur toute route (lecture refusée par
  Windows comprise), 409 `export_verrouille` aussi quand le docx est ouvert juste après
  l'écriture.
- **etat-v2.md** : ajouter `relecture_illisible` (409) à la table §26 ; corriger la mention
  « verrou de fichier » de R2 en « verrou de processus ».
