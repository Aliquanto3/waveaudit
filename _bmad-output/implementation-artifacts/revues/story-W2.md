# Revue — story W2 (accueil v2, lots récents et suivi lu sur le disque)

Commit relu : 6d32a61 (base dfc0886), branche `worktree-agent-a177238466a5d4079`. Q5 en
parallèle (`prompt.py`, `pipeline.py`, `config/artefacts.toml`, `u/test_composition.py`) :
fichiers disjoints, non touchés.
Verdict : conforme à §26 (ordre de lancement A1/A2, refus après l'id, 409 avec `occupation`,
`dossier_lot_existant` partout), §30 et §11 ; un défaut moyen et quatre faibles corrigés, la
redirection 303 `/lots/{id}` → `/incidents/{id}` ajoutée.

| Sévérité | Source | Constat | Décision |
|---|---|---|---|
| moyenne | second avis 1 | `POST /lots` sans champ `langue` : `lot.json` écrit avec `langue=null` avant le 303, puis `executer_lot` ne le réécrit pas (sans effet si présent). `ResumeLot.langue` reste `null` et la relecture vide retombe sur `"fr"` même avec `fiches.langue="en"`. Contraire à §9 v2 étape 1 et à la consigne R2 pour W2. | Corrigé : la route écrit `langue or config.fiches.langue`. Test `e2e::test_lot_json_porte_la_langue_resolue_sans_champ_langue` (config en `en`) ; `test_modele_et_langue_recus_par_le_lot` vérifie aussi `lot.json` (`modele_demande` `null` en externe, `langue` `en`) : l'ancien oracle (`model` reçu par le faux moteur) ne distinguait pas `None` de `modele_api`. |
| moyenne → faible | second avis 2 | Lifespan : `fermer()` synchrone dans la coroutine ; il attend le verrou interne de `MoteurALaDemande`, tenu pendant une ouverture de llama-server (jusqu'à `delai_demarrage_s`). Boucle d'événements bloquée et arrêt au-delà de 10 s. | Corrigé en partie : `await asyncio.to_thread(fermer)` (boucle libre, second Ctrl+C opérant) ; même chose pour `fermer()` dans `POST /lots` (`run_in_threadpool`). Reporté : borner l'attente demande un `fermer` non bloquant dans `moteur_demande.py` (M1, hors périmètre) ; cas limité à un arrêt pendant le démarrage d'une régénération. Écart M1 d'`etat-v2.md` : à clore avec cette décision. |
| faible | second avis 3 | `except Exception: pass` dans le fil : un refus avant `JournalLot` (dossier absent, id déjà exécuté) laisse un lot `interrompu` sans trace. | Corrigé : `_log.warning(..., exc_info=True)`. |
| faible | second avis 4 | `prendre` échoue puis le verrou est rendu avant `occupation()` : `_refus_lot_en_cours(None)` → `AttributeError`, 500. | Corrigé : `None` toléré (« --:-- », `occupation: null`). Test `e2e::test_refus_lot_en_cours_occupation_liberee_entre_temps`. |
| faible | second avis 5 | `GET /` appelle `lister_lots` (tous les journaux relus, psutil) pour un booléen. | Corrigé : `lots.existe_un_lot(config)` (tests d'existence seulement). Test `u::test_existe_un_lot`. |
| faible | second avis 6 | Test `test_pages_portent_le_jeton…` : `POST /lots` sans faux moteur ni attente de fin. | Rejeté : `config_test` pointe déjà vers un faux moteur nominal et le test se termine par `_attendre_fin`. |
| faible | second avis 7 | Message « Un lot est déjà en cours » affiché aussi pendant une régénération. | Rejeté : texte de Voice and Tone repris tel quel (§26) ; le lien mène au lot régénéré, ce qui reste juste. À revoir en recette si gênant. |
| moyenne | reviewer | §26 : « Une page `/lots/{id}` d'un lot incident redirige (303) vers `/incidents/{id}` » non fait (reporté à W4 par le dev). Ce sens vit dans `pages.py`, que W4 ne doit pas toucher (stories.yaml : W4 seulement dans son routeur). | Corrigé : `lots.workflow_lot(dossier)` et 303 dans `page_lot`. Test `e2e::test_page_d_un_lot_incident_redirige`. Le sens inverse (`/incidents/{id}` d'un lot de fiches → `/lots/{id}`) reste à W4. |
| faible | reviewer | `cree_le` sans fuseau (lot.json retouché) : comparaison naïve/avec fuseau → `TypeError` au tri, 500 sur `/lots` et `/api/lots`. | Corrigé : `_date` ajoute le fuseau local. Test `u::test_cree_le_sans_fuseau_trie_sans_erreur`. |
| — | reviewer | Complexité : 2 constats. (1) `lister_lots` relisait tous les journaux de `var/sorties/` à chaque `GET /lots` et `/api/lots` (et `GET /`) avant de garder 50 lots : O(historique × taille des journaux), croissant sans borne. (2) `GET /lots/{id}/etat` relit tout le journal à chaque sondage (1 s) : O(n²) sur un lot. | (1) Corrigé : tri sur `lot.json` (ou le journal lu jusqu'à `lot_demarre`), journaux complets relus pour les 50 retenus seulement. Test `u::test_au_plus_50_les_plus_recents`. (2) Laissé : imposé par §30 (« relu à chaque appel ») ; ~4 lignes par note, quelques centaines de lignes par lot. |
| faible | dev (écart) | `date_creation_processus(pid)` ajouté dans `adaptateurs/memoire_psutil.py`, fichier non listé. | Accepté : `test_architecture.py` réserve psutil aux adaptateurs ; fonction minimale, `AccessDenied` → `None` (lot alors lu `interrompu`, prudent). |
| faible | dev (écart) | Redirection 303 `/lots` ↔ `/incidents` reportée à W4. | Corrigé en partie (voir ligne reviewer) : sens `/lots` → `/incidents` fait ici, sens inverse à W4. |

Vérifié conforme : ordre §26 (occupation provisoire, validation, `nouvel_id_lot`, `definir`,
écriture, `lot.json`, `fermer`, fil daemon, `liberer` en `finally`) ; refus après l'id →
`var/entrees/<id>` et `var/sorties/<id>` supprimés ; `RuntimeError` de `start()` couverte par
le même `finally` ; modèle validé contre `modeles_installes`, externe passé `None` ; tri
`cree_le` puis `id_lot` ; `etat` selon journal, occupation, pid (`os.getpid()` exclu) ;
gabarits autoéchappés, aucun script en ligne ; aucun GET n'écrit (test existant vert).

Tests : ciblés 83 verts ; `tests/unitaires` et `tests/e2e` 993 verts ; ruff check et format
propres.

## Interfaces et consignes pour la suite

- **X2 (CLI `exporter`)** : état d'un lot par `lots.etat_lot(config, id, occupation=None)` ;
  refuser `en_cours` (vivant dans un autre processus, ou ce processus) ; dossier par
  `lot.dossier_lot_existant`, jamais `verifier_id_lot`.
- **W4 (incident)** : même ordre de lancement que `routeurs/lots.creer_lot` (copier le motif :
  occupation provisoire `("incident", "", None, debut)`, `definir`, `ecrire_fiche_lot(...,
  workflow="incident", langue=None)`, `await run_in_threadpool(moteur.fermer)`, fil daemon
  avec `liberer` et log en `finally`/`except`). `GET /incidents/{id}` d'un lot de fiches →
  303 `/lots/{id}` (`lots.workflow_lot`). `/incidents/{id}/etat` : `lots.etat_lot` (même
  forme). Ne pas toucher `pages.py`.
- **W3a (relecture)** : `request.app.state.config`, `.verrou`, `.moteur` (plus
  d'`app.state.lots`). Écritures refusées 409 `lot_en_cours_externe` quand
  `lots.etat_lot(...)["etat"] == "en_cours"` et que `verrou.occupation()` ne porte pas ce lot ;
  `lot_en_cours` quand l'occupation le porte. Pour le seul booléen « externe », lire
  `lister_lots` serait trop cher : utiliser `etat_lot` sur le lot visé.

## Écarts à arbitrer

- `MoteurALaDemande.fermer()` bloquant pendant une ouverture (écart M1) : attente d'arrêt non
  bornée à 10 s si l'arrêt tombe pendant le démarrage d'une régénération. Proposition :
  accepter (POC) ou story M1-bis (`fermer(timeout)`).
- Fil de lot `daemon` : un arrêt de l'UI pendant un lot tue le fil sans `finally`, le
  llama-server du lot peut survivre au processus (préexistant v0.1.0). Vérification sur
  l'EliteBook en REC : arrêter l'UI pendant un lot, puis `tasklist | findstr llama-server`.
