---
id: W3a
title: API de relecture, régénération et export
status: review
sources:
  - ../stories.yaml
  - ../SPEC.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/impacts-v2.md
  - ../../../planning-artifacts/ux/EXPERIENCE.md
---

# Story W3a — API de relecture, régénération et export

## Livré

`interfaces/web/routeurs/relecture.py` seulement (inclus par W1 ; `app.py`, `pages.py`,
`composition.py`, `export_docx.py` non touchés). Aucun gabarit ni JS (W3b).

| Route | Succès | Erreurs |
|---|---|---|
| `GET /lots/{id}/relecture` | 200 `{"id_lot","langue","modele","etat_lot","non_validees","entrees":[{"index","note","etat","statut_generation","statut_relecture","generation","version","titre"}]}` | 404 `lot_inconnu` ; 409 `relecture_illisible` |
| `GET /lots/{id}/entrees/{index}` | 200 `{"entree","fiche_courante","candidats_detail":[{"id","score","titre"}],"generable","modifiable"}` | 404 `lot_inconnu`, `entree_inconnue` ; 409 `relecture_illisible` |
| `GET /lots/{id}/catalogue` | 200 `{"constats":[{"id","famille","titre"}]}`, trié par id, langue du lot | 404 ; 409 `relecture_illisible` |
| `PUT /lots/{id}/entrees/{index}/correction` | 200 `{"entree"}` | 404 ; 409 `conflit_version` (+`entree`), `generation_en_cours`, `lot_en_cours_externe`, `relecture_illisible` ; 422 `corps_invalide`, `non_modifiable`, `rubrique_trop_longue`, `reference_ajoutee`, `reference_dupliquee` ; 503 `ecriture_impossible` |
| `POST /lots/{id}/entrees/{index}/validation` | 200 `{"entree"}` | 404 ; 409 `conflit_version` (+`entree`), `generation_en_cours`, `lot_en_cours_externe` ; 422 `corps_invalide`, `non_modifiable`, `vecteur_invalide`, `rubrique_vide` ; 503 |
| `POST /lots/{id}/entrees/{index}/candidat` | 202 `{"entree"}` (`generation="en_cours"`) | 404 ; 409 `lot_en_cours_externe`, `lot_en_cours` (+`occupation`), `conflit_version` (+`entree`), `confirmation_requise` ; 422 `corps_invalide`, `modele_indisponible`, `non_generable`, `source_absente`, `candidat_courant`, `candidat_inconnu` ; 503 |
| `POST /lots/{id}/export` `{"type"}` | 200 docx, `Content-Disposition` `rapport-<id>.docx` / `brouillon-<id>.docx`, `X-Non-Validees` en final | 404 `lot_inconnu`, `lot_incident` ; 409 `lot_en_cours`, `lot_en_cours_externe`, `aucune_fiche_validee`, `export_verrouille`, `relecture_illisible` ; 422 `type_invalide` |

- Lectures : `relecture.charger(dossier, occupation=verrou.occupation())` (génération
  interrompue présentée sans écriture) ; `etat_lot` via `lots.etat_lot` sur le lot visé.
- Écritures, dans l'ordre : 404 (lot, puis entrée hors `1..n`), lecture (illisible → 409),
  409 `lot_en_cours_externe` (lot `en_cours` sans que l'occupation locale le porte), puis
  `relecture.modifier(..., occupation=verrou.occupation())` avec `corriger` (CVSS recalculé par
  le domaine, jamais repris du client) ou `valider`. `OSError` → 503 `ecriture_impossible`.
- Candidat : 422 `modele_indisponible` avant le verrou (local-gere : modèle du lot absent de
  `modeles_installes` ; seulement si l'entrée a une source), puis
  `prendre(Occupation("regeneration", id, index))` (échec : 409 `lot_en_cours`), puis
  `demarrer_regeneration(..., ids_catalogue=...)` sans occupation ; tout refus libère le verrou ;
  fil daemon `relecture.regenerer`, `liberer()` dans son `finally`.
- Export : `run_in_threadpool` → `exporter_lot(config, id, mode, occupation=...)` ;
  `lot_en_cours` traduit en `lot_en_cours_externe` si l'occupation ne porte pas le lot ;
  `PermissionError` → 409 `export_verrouille` ; docx lu en mémoire (aucun descripteur laissé
  ouvert qui bloquerait l'`os.replace` d'un export suivant). GET → 405, rien n'est écrit.

## Tests

- Nouveaux, `e2e/test_relecture_ui.py` (23) : fiche ouvrable pendant un lot lent et
  progression monotone ; correction relue après recréation de l'app, CVSS du serveur,
  correction identique sans incrément ; vecteur invalide enregistré puis validation refusée ;
  `reference_ajoutee`, `reference_dupliquee`, `corps_invalide`, `rubrique_trop_longue` ;
  validée puis modifiée → `a_valider`, `non_validees` ; `conflit_version` avec `entree` ;
  changement de candidat (`candidat_courant`, `candidat_inconnu`, `confirmation_requise`,
  verrou libéré, nouveau `constat_id` dans `<constat>`, garde-fous) ; 409 `lot_en_cours` sur
  candidat et export pendant un lot ; `non_rattachee` → fiche sur un id du catalogue hors
  candidats, `non_traitee` → 422 `non_generable` ; export final et brouillon relus par
  python-docx (marque, annexe des non validées, `X-Non-Validees`) ; GET export → 405 sans
  fichier ; `export_verrouille` ; lot échoué relisible et exportable ; catalogue trié en
  anglais ; génération `en_cours` orpheline lue sans écriture puis relancée ; lot en cours dans
  un autre processus → 409 `lot_en_cours_externe` sur les quatre écritures ; `os.replace` en
  échec → 503 sans changement ; index 0 et n+1 → 404 ; modèle désinstallé → 422 ;
  `relecture.json` illisible → 409 `relecture_illisible` ; lot inconnu et lot incident → 404 ;
  régénération en cours → 409 `lot_en_cours`.
- Nouveau, `e2e/test_hors_ligne.py::test_ui_changement_de_candidat_sous_garde_sans_tentative`.
- Réalignés : aucun (le routeur était vide ; aucun test existant ne lisait ces routes).

## Choix d'interprétation

- `relecture_illisible` (arbitrage d'Anaël sur R2) : statut 409, message sans chemin
  (`relecture.json` cité par son nom seul).
- Correction et validation restent permises pendant un lot de **ce** processus (table du §26 :
  seul `lot_en_cours_externe` y figure) ; l'écriture concurrente avec `enregistrer_resultat`
  est sérialisée par le verrou de processus de R2 (`threading.Lock`).
- `generable` = entrée `fiche` ou `ecartee` `non_rattachee`, source présente, pas de
  génération en cours, lot non tenu par un autre processus, modèle disponible. Il ne tient pas
  compte du verrou local (un lot qui tourne donne 409 `lot_en_cours` au POST).
  `modifiable` = entrée `fiche`, pas de génération en cours, lot non externe.
- `occupation` du 409 `lot_en_cours` porte aussi `index` (régénération).
- Corps JSON : champs stricts (`StrictInt`, `StrictStr`, `StrictBool`), champs inconnus ignorés ;
  `cvss_vecteur` borné à 100 caractères dès le corps (422 `corps_invalide`). Un id de référence
  inconnu passe à `corriger` sous une référence de façade pour garder l'ordre des refus du §25.

## Reports

- Écran (tiroir, onglets, formulaire, exports) : W3b.
- Le catalogue est relu sur disque à chaque `GET …/entrees/{index}` et `…/catalogue` (50
  entrées, rapide) ; un cache est possible si W3b le sondait souvent.

## Écarts au contrat

- §26 : `relecture_illisible` absent de la table (arbitrage d'Anaël, à y ajouter).
- §26 : `generation_en_cours` listé pour `POST …/candidat` est inatteignable (verrou d'abord :
  409 `lot_en_cours`), comme arbitré sur R2.

## Revue

- faible, second avis 1 : `RecursionError` de `json.loads` → 500 ; corrigé (422 codé).
- faible, second avis 2 : `OSError` à la lecture de `relecture.json` → 500 ; corrigé (409 `relecture_illisible`).
- faible, second avis 3 : `read_bytes` du docx hors `try` → 500 ; corrigé (409 `export_verrouille`).
- faible, second avis 4 : lot sans modèle consigné refusé en local-gere ; corrigé (modèle par défaut).
- faible, second avis 5 : contrôle externe hors verrou inter-processus ; rejeté (la CLI ne reprend pas un lot existant).
- écarts du dev (`relecture_illisible` 409, `index` dans `occupation`, écritures pendant un lot local) : acceptés.
- Complexité : 1 constat (relecture et journal relus à chaque sondage) ; laissé, motif du §30.
Détail : `implementation-artifacts/revues/story-W3a.md`.
