---
id: ARR
title: Arrêt propre de l'UI — llama-server enfant et fermer(timeout)
status: review
sources:
  - ../../../implementation-artifacts/etat-v2.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/ARCHITECTURE-SPINE.md
---

# Story ARR — Arrêt propre de l'UI

Story ajoutée par arbitrage (2026-10-18), hors `stories.yaml`, pour corriger deux écarts
constatés à l'arrêt de l'UI (`etat-v2.md`, « Écarts à arbitrer » M1 et W2, `revues/story-W2.md`) :

1. un lot ou un incident interrompu pendant son exécution (fil `daemon`) pouvait laisser un
   llama-server orphelin, le fil mourant sans exécuter son `finally` ;
2. le lifespan (§24, revue E3) attendait l'usage en cours 10 s au plus, mais `fermer()` du
   moteur à la demande pouvait ensuite attendre son verrou interne jusqu'à
   `delai_demarrage_s` (120 s) si une ouverture était en cours : la borne de 10 s n'était pas
   tenue en pratique.

## Livré

- `adaptateurs/llama_server.py` : chaque `LlamaServer` s'enregistre dans un registre de
  processus (module-level, verrou `threading.Lock`) dès que son sous-processus est lancé, et
  s'en retire à `_arreter()` (désormais protégée par un verrou d'instance, pour un appel
  concurrent sûr entre le fil qui a ouvert le serveur et le filet de sécurité).
  `terminer_tous()` termine tout serveur encore suivi par ce processus, sans toucher un
  processus qui n'aurait pas été lancé par ce module ; enregistrée via `atexit.register` au
  chargement du module (filet pour une sortie imprévue).
- `application/composition.py` : `terminer_llama_server_en_cours()`, seul point d'accès de
  l'application à ce filet (AD-1 : `adaptateurs.llama_server` reste importé au niveau module
  par `composition` seule).
- `application/moteur_demande.py` : `MoteurALaDemande.fermer(timeout: float | None = None)`.
  Sans `timeout` (défaut), comportement inchangé. Avec un `timeout`, tente le verrou interne
  borné (`Lock.acquire(timeout=...)`) ; au-delà, n'attend pas davantage et appelle
  `composition.terminer_llama_server_en_cours()` : le llama-server en cours d'ouverture est
  terminé directement, ce qui fait échouer le sondage `/health` en cours côté `LlamaServer`
  (`MoteurInjoignable`) et libère le verrou interne de lui-même, sans intervention
  supplémentaire de `fermer`.
- `interfaces/web/app.py` (`_lifespan`) : après l'attente bornée de la fin de l'usage en cours
  (inchangée), `fermer(timeout=<reste de la borne de 10 s>)` au lieu de `fermer()` sans borne ;
  puis `composition.terminer_llama_server_en_cours()` en filet général, pour le llama-server
  d'un lot ou d'un incident encore en cours dans un fil `daemon` distinct du moteur à la
  demande (AD-20).
- Lot ou incident interrompu : l'état lu sur le disque reste `interrompu` (§30,
  `application/lots.py`), sans changement — rien n'écrit un état supplémentaire.

## Tests

- `tests/unitaires/test_llama_server.py` : `terminer_tous()` termine un faux llama-server lancé
  sans passer par `__exit__` (comme un fil mort sans `finally`), sans toucher un autre
  processus lancé hors de ce module (vrai sous-processus Python, non suivi).
- `tests/unitaires/test_moteur_demande.py` : `fermer(timeout=...)` avec un faux lanceur dont
  l'ouverture bloque jusqu'au déclenchement du filet (`composition.terminer_llama_server_en_cours`
  monkeypatché) ; `fermer` rend la main bien avant le délai réel d'ouverture. `fermer()` sans
  `timeout` : comportement inchangé (test de non-régression).
- `tests/e2e/test_app_lifespan.py` (nouveau) : UI réelle (FastAPI + `TestClient`), ouverture de
  régénération simulée bloquée (faux `LlamaServer`), arrêt du `TestClient` pendant cette
  ouverture ; la fermeture du client (déclenche le lifespan) reste bornée et le filet est
  appelé. `ATTENTE_ARRET_MOTEUR_S` raccourcie par `monkeypatch` pour un test rapide.
- `tests/e2e/test_reel.py` (marqueur `slow`, non lancé par cette story) :
  `test_ui_reel_arret_pendant_un_lot_ne_laisse_pas_de_llama_server` — `waveaudit ui` réel en
  sous-processus, un lot d'une note démarré par HTTP, attente que llama-server démarre, arrêt
  du processus (`CTRL_BREAK_EVENT` sous Windows, `terminate()` ailleurs), puis vérification
  par `psutil` qu'aucun llama-server ne subsiste parmi les anciens descendants du processus.

## Reports

- Écart au contrat : `contrats.md` §24 ne documente que `fermer()` sans paramètre ; cette story
  ne modifie ni `SPEC.md`, ni `ARCHITECTURE-SPINE.md`, ni `contrats.md` (consigne explicite de
  l'arbitrage). À reporter : documenter `fermer(timeout)` dans `contrats.md` §24 lors d'une
  prochaine story de contrat.
- Test `slow` ajouté mais non exécuté dans cette story (une autre story pouvait tourner en
  parallèle) : à lancer avant intégration finale, ou en CI nocturne avec `var/modeles` installé.
- `routeurs/relecture.py` et `routeurs/lots.py` non touchés au-delà du nécessaire : seul
  `interfaces/web/app.py` (lifespan) a changé côté interfaces/web.
