---
id: story-12
title: Composition, lot et cycle de vie de llama-server
status: review
sources:
  - ../stories.yaml
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
---

# Story 12 — Composition, lot et cycle de vie de llama-server

## Livré

- `application/lot.py` : `nouvel_id_lot(var)` (`AAAAMMJJ-HHMMSS`, suffixes `-2`, `-3`… par
  `mkdir(exist_ok=False)`) et `executer_lot(requete, config, abonne=None)` (contrats §9) :
  dossier de sortie, `composition.ouvrir` une fois, `sonder()`, `lot_demarre`
  (`id_lot`, `modele`, `pid_moteur`), `fiche_demarree` puis `fiche_terminee` /
  `fiche_non_traitee` / `fiche_non_rattachee` (index 1..total, durée), `fiches.json`
  (`Rapport.model_dump(mode="json")`), `rapport.docx`, copie `copie_rapport`, `lot_termine`.
  Seul écrivain de `journal.jsonl` (une ligne, flush, avant l'abonné) ; exception de l'abonné
  journalisée et ignorée. Toute exception sortante émet `lot_echoue`
  (`erreur`, `message`) puis remonte ; les chemins absolus du message sont réduits à leur nom.
- `application/composition.py` : `ouvrir(config, modele, *, id_lot=None)`, `choisir_modele`,
  `creer_mesure_memoire()`. Externe : `base_url` (vide -> `ConfigurationInvalide`), `modele`
  surcharge `modele_api`, `pid=None`. Local-gere : manifeste, modèle explicite (rôle modèle
  exigé), sinon défaut, ou repli si RAM disponible < `ram_min_defaut_go` Gio ; binaire ou poids
  absents -> `ConfigurationInvalide` (« lancer `waveaudit installer` ») ; `LlamaServer` avec
  `ctx`, `threads`, `delai_demarrage_s` et le journal `var/journaux/llama-server-<id_lot>.log`.
  Le thème privé est validé (`ExportDocx`) avant tout démarrage du moteur.
- `adaptateurs/llama_server.py` : `LlamaServer` (contrats §10) : port libre sur 127.0.0.1,
  ligne de commande exacte, sortie dans le journal, Job Object `KILL_ON_JOB_CLOSE` par ctypes
  et `OpenProcess` (Windows), attente `/health` dans le délai, un seul nouvel essai sur un autre
  port si le processus meurt, sinon `MoteurInjoignable` ; arrêt `terminate`/`wait(5)`/`kill`
  puis fermeture des handles, y compris quand le démarrage échoue.
- `adaptateurs/memoire_psutil.py` : `MesureMemoirePsutil.rss_octets` (None si le processus a
  disparu) et `ram_disponible_octets()`.
- Tests : `tests/e2e/test_lot.py` (20 notes de démo, journal, id unique dans la même seconde,
  sonde KO, abonné qui lève, copie, CAP-9 deux faux moteurs, entrées invalides, message sans
  chemin absolu) ; `tests/unitaires/test_composition.py` (RAM monkeypatchée, externe, local-gere
  avec `LlamaServer` factice) ; `tests/unitaires/test_llama_server.py` avec le faux binaire
  `tests/faux_llama_server.py` (port, arguments, nouvel essai, délai dépassé, Job Object) ;
  `tests/e2e/test_llama_reel.py` marqué `slow`.

## Écarts au contrat (variantes minimales)

- `ouvrir` reçoit en plus un mot-clé optionnel `id_lot` : le journal de llama-server est nommé
  par `id_lot` (contrats §10) alors que la signature §9 ne le transmet pas. Sans lui,
  horodatage `AAAAMMJJ-HHMMSS`.
- `lot_echoue` est émis pour toute exception sortante (pas seulement la sonde), pour que le banc
  (§20) s'arrête toujours. Les vérifications sans effet (workflow inconnu, dossier absent,
  `id_lot` hors `[0-9A-Za-z-]`) lèvent `EntreeInvalide` avant la création du dossier de sortie,
  donc sans journal.
- Faux binaire lancé par `sys._base_executable` (repli `sys.executable`) : sous Windows, le
  `python.exe` du venv est un lanceur qui crée un processus enfant (pid et arrêt faussés).
  `gguf = Path("faux_llama_server")` est passé en `-m` : `python -m faux_llama_server`.
- Seuil RAM en Gio (`1024**3` octets), choix prudent qui favorise le repli.

## Reports

- Moteur tombé en cours de lot : le contrat (AD-6) prévoit un repli immédiat `repli_moteur`
  par note, sans arrêt du lot ; avec `timeout_s = 180` en local-gere, chaque note restante peut
  attendre jusqu'au délai si le moteur ne répond plus sans refuser la connexion. Pas de
  disjoncteur dans le contrat : à arbitrer hors story.
- Un échec de copie vers `copie_rapport` (fichier verrouillé) remonte en `OSError` après
  `lot_echoue` ; le code retour CLI associé relève de la story 13.

## Revue

| Sévérité | Source | Constat | Décision | Motif |
|---|---|---|---|---|
| medium | second avis 4 + reviewer | `_sans_chemin` coupait au premier espace : `C:\Users\Prénom Nom\…` laissait `Nom\proj\…` (nom du poste) dans `journal.jsonl` ; il tronquait aussi les URL (`http://…/v1` -> `httv1`, lettre de lecteur précédée d'une lettre). | corrigé | §9 : jamais de chemin absolu dans le journal. Un espace reste dans le chemin si le mot suivant contient un séparateur ; chemin entre apostrophes pris en entier ; lecteur non précédé d'un caractère de mot. Tests `test_sans_chemin_*`. |
| medium | reviewer | `test_job_object_tue_l_enfant_a_la_fermeture` instable : `psutil.Process(pid)` lève `NoSuchProcess` si l'enfant meurt entre `pid_exists` et `Process` (échec observé en première exécution). | corrigé | `_attendre_fin` traite `NoSuchProcess` comme « fini ». |
| medium -> low | second avis 1 | `fiches.json` écrit sans fichier temporaire ni `os.replace`. | rejeté | Le contrat ne demande pas d'écriture atomique ; un échec d'écriture émet `lot_echoue`, et l'UI ne lit `fiches.json` qu'après `lot_termine`. |
| medium | second avis 2 | Aucun `garde(` autour du lot. | rejeté (relève des stories 13 et 14) | Contrats §12 et AD-9 : la garde est posée par les commandes `fiches`, `ui` et `banc`, après `charger_configuration()`, autour de tout le reste ; `executer_lot` ne la pose pas. **À mettre dans le prompt des stories 13 (CLI) et 14 (UI)**, et du banc : `with garde(config.reseau.hotes_autorises):` englobant l'appel à `executer_lot`, imports d'adaptateurs hors niveau module de `cli.py`. |
| low | second avis 3 | Job Object assigné après `Popen` d'un enfant non suspendu. | rejeté | Ordre imposé par contrats §10 (`OpenProcess` sur le pid) ; llama-server ne crée pas d'enfant ; un échec d'assignation lève et `__enter__` arrête le processus. |
| low | second avis 5 | `id_lot` réservé Windows (`NUL`) : `mkdir` « réussit » sans créer de dossier, puis `FileNotFoundError` brute. | corrigé | Contrôle `is_dir()` après `mkdir` -> `EntreeInvalide` (test sous Windows). Le même `id_lot` passé deux fois ajoute au même journal : rejeté, l'appelant (UI, §18) obtient l'id par `nouvel_id_lot`, unique. |
| low | second avis 6 | Course sur `port_libre` (un autre service pourrait prendre le port). | rejeté | Méthode imposée par §10 ; un serveur étranger sur le port ferait mourir llama-server au bind, ce qui déclenche le nouvel essai sur un autre port. |
| low | second avis 7 | Une exception de `traiter` autre que `SortieInvalide`/`MoteurInjoignable` arrête le lot. | rejeté | AD-6 : le workflow absorbe ces deux erreurs ; toute autre exception est un défaut, et §4 lui donne le code 4. La convertir en repli masquerait le défaut. |
| info | reviewer | `ouvrir(..., id_lot=)` en argument nommé optionnel, hors signature §9. | accepté, à consigner | Nécessaire pour nommer `llama-server-<id_lot>.log` (§10) ; compatible avec la signature du contrat. |
| info | reviewer | Complexité : 0 constat. | — | Journal écrit ligne à ligne avec flush, résultats en liste par ajout : O(1) par événement, aucun parcours complet. |

Tests : ciblés verts (`test_lot.py`, `test_composition.py`, `test_llama_server.py`, 26 après revue) ; suite complète 238 verts ; ruff check et format verts. Aucun vrai llama-server, aucun processus orphelin.
