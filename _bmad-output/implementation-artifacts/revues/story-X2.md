# Revue — story X2 (service d'export et `waveaudit exporter`)

Commit relu : afb3fee (base 67ed56a), branche `worktree-agent-a0245ca2369b09de8`. LIB
(`adaptateurs/export_docx.py`) et W4 (routeurs web) en parallèle : non touchés.
Verdict : conforme à §27 étapes 1, 2, 4, 5, au verrou par chemin (E19) et à la CLI ; un défaut
moyen (étape 3, verrou de ce processus) et deux faibles corrigés.

| Sévérité | Source | Constat | Décision |
|---|---|---|---|
| moyenne | second avis 1 | `exporter_lot` appelait `lots.etat_lot(config, id, None)` : un lot en génération dans le même processus (route web W3a) est lu `interrompu` (`_pid_vivant_externe` écarte `os.getpid()`) et exporté en pleine génération. Contraire à §27 étape 3 (« verrou de ce processus »). | Corrigé : paramètre nommé `occupation: Occupation \| None = None`, passé à `etat_lot` et à `charger` ; refus `lot_en_cours` aussi quand l'occupation porte ce lot (régénération d'une de ses fiches, §26 « refusé tant que ce lot tourne »). Test `u::test_lot_en_cours_dans_ce_processus` (pid = `os.getpid()`, occupation `fiches` puis `regeneration`, autre lot non bloqué). |
| faible | second avis 2 | `charger(dossier)` sans occupation : une régénération vivante présentée « échec, génération interrompue ». | Rejeté : `rapport_export` ne lit pas `generation` (fiches prises par `fiche_courante`), le docx est inchangé ; l'occupation est de toute façon passée désormais, et une régénération de ce lot dans ce processus est refusée. Régénération dans une autre instance de l'UI : non détectable (aucun pid de régénération sur le disque), sans effet sur le docx (la fiche courante reste celle d'avant la régénération). |
| faible | second avis 3 | `_VERROUS` jamais purgé. | Rejeté : au plus deux entrées par lot, même schéma que `application/relecture._VERROUS` ; borné par `var/sorties/`. |
| faible | second avis 4 | `test_exporter_final_code_0_bandeau_et_fiches_non_validees` asserte le code 2. | Corrigé : renommé `test_exporter_final_sans_fiche_validee_code_2`. |
| faible | second avis (non-constat) / reviewer | §27 : `PermissionError` → code 4 « fermez le document dans Word » ; le message commun disait seulement « accès refusé ». | Corrigé dans la commande `exporter` (ajout seul, `_codes_retour` inchangé) : « exporter : accès refusé (<nom>), fermez le document dans Word ». Test code 4 complété (message, aucun `.partiel` restant). |
| — | second avis (non-constat) | Bandeau de fin non émis sur erreur. | Conforme : même comportement que les autres commandes (§19). |
| — | reviewer | Complexité : 0 constat. Un export relit `journal.jsonl` et `relecture.json` une fois (O(n)) ; aucune structure ne grossit pendant l'exécution hors `_VERROUS` (ci-dessus). | — |

Vérifié conforme : `dossier_lot_existant` seul (aucun dossier créé sur un lot inconnu) ; lot
incident v0.1.0 reconnu par `incident.json` ; `aucune_fiche_validee` en final ; écrasement,
provisoire unique et quatre exports simultanés sans résidu ; `garde(...)` autour du service ;
`creer_exporteur` seul point d'instanciation ; aucune validation par la CLI.

Tests : ciblés 21 verts ; `tests/unitaires` et `tests/e2e/test_cli.py` 908 verts ; ruff check
et format propres.

## Interfaces et consignes pour la suite

- **W3a (`POST /lots/{id}/export`)** : appeler
  `exporter_lot(config, id_lot, mode, occupation=request.app.state.verrou.occupation())`, dans
  le fil (`run_in_threadpool`). Traduction des refus (§26) : `lot_inconnu` et `lot_incident` →
  404 ; `lot_en_cours` → 409 `lot_en_cours` si l'occupation porte ce lot, sinon 409
  `lot_en_cours_externe` (le service ne distingue pas : il lève `lot_en_cours` dans les deux
  cas, comme §27) ; `aucune_fiche_validee` → 409 ; `PermissionError` → 409
  `export_verrouille` ; `type` hors `final`/`brouillon` → 422 `type_invalide` avant l'appel.
  Succès : docx en pièce jointe (`chemin.name`), en final `X-Non-Validees: <n>` (second élément
  renvoyé).

## Écarts à arbitrer

- Signature d'`exporter_lot` : §27 la donne sans `occupation` ; ajout d'un paramètre nommé
  optionnel (CLI inchangée). À reporter dans `contrats.md` §27 à la prochaine mise à jour.
