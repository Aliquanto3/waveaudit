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

Tests : ciblés verts (`test_lot.py`, `test_composition.py`, `test_llama_server.py`).
