---
id: story-14
title: UI web locale
status: review
sources:
  - ../stories.yaml
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
---

# Story 14 — UI web locale

## Livré

- `interfaces/web/app.py` : `creer_app(config) -> FastAPI` (contrats §18). N'active pas le
  garde réseau (AD-9) : c'est à l'appelant (commande CLI `ui`, story 13) de poser
  `with garde(config.reseau.hotes_autorises):` autour du service et de lancer
  `uvicorn.run(app, host=config.ui.hote, port=config.ui.port)`.
- Middleware : en-tête `Host` différent de `127.0.0.1:<port>`, `localhost:<port>` ou
  `testserver` -> HTTP 400 ; `POST` dont `Origin` est présent et hors de ce même ensemble
  (préfixé `http://`) -> HTTP 403.
- `GET /` : page d'envoi (formulaire multipart, champ `notes`, plusieurs fichiers).
- `POST /lots` : verrou `threading.Lock` non bloquant pris avant toute écriture (409 sans
  écriture s'il est déjà pris) ; validation de chaque nom (regex contrats §18, nom réservé
  Windows, doublon de casse, 1 Mo maximum) avant toute écriture, 400 au premier refus et verrou
  relâché ; sinon `nouvel_id_lot`, écriture dans `var/entrees/<id_lot>/`, thread `daemon` qui
  exécute `executer_lot` et relâche le verrou dans un `finally` ; redirection 303 vers
  `/lots/<id_lot>`.
- `GET /lots/{id}` : page de suivi (bandeau, JS `static/etat.js` qui interroge `.../etat`).
- `GET /lots/{id}/etat` : `{"id_lot", "etat", "evenements", "erreur"}`, état en mémoire protégé
  par un verrou et copié à la lecture ; 404 si l'id est inconnu.
- `GET /lots/{id}/rapport.docx` : 404 si le lot est inconnu, 409 s'il n'est pas terminé, sinon
  le fichier.
- `templates/` (Jinja2 : `base.html`, `index.html`, `lot.html`) et `static/` (`style.css`,
  `etat.js`) : bandeau `Démonstration — données fictives` sur chaque page, aucune URL externe.
- Tests `tests/e2e/test_ui.py` (`TestClient`, `config_test`, faux moteur) : bandeau sur chaque
  page, absence d'URL externe, 20 notes -> 303 -> attente de `termine` -> téléchargement d'un
  `.docx` valide, second envoi pendant un lot -> 409 sans écriture, noms refusés (`../x.md`,
  `CON.md`, doublon de casse, `.exe`, > 1 Mo) -> 400, `Host` étranger -> 400, `Origin` étranger
  -> 403, rapport avant la fin -> 409, lot inconnu -> 404 (`etat` et `rapport.docx`).

## Écarts au contrat (variantes minimales)

- Le bandeau `BANDEAU` est redéfini en constante locale dans `interfaces/web/app.py` au lieu
  d'être importé d'`adaptateurs/export_docx.py` : `tests/unitaires/test_architecture.py`
  interdit à `interfaces/web/` d'importer un adaptateur, même à l'intérieur d'une fonction.
  Même littéral que `export_docx.BANDEAU`, à garder synchronisé si ce texte change.
- Validation de nom : le contrat dit « `Path(nom).name` doit correspondre à l'expression » ; le
  code compare en plus `Path(nom).name` au nom brut reçu, pour refuser `../x.md` (que
  `Path(...).name` ramènerait sinon à `x.md`, valide) — nécessaire pour satisfaire le parcours
  de test demandé (`invoke_dev_with`).

## Reports

- Branchement CLI (hors périmètre de cette story, propriété de la story 13) : la commande
  `ui [--port N] [--config F]` doit faire `config = charger_configuration(...)`, refuser de
  démarrer (code 2) si `config.ui.hote` n'est pas `127.0.0.1` ou `::1`, puis
  `with garde(config.reseau.hotes_autorises): uvicorn.run(creer_app(config), host=config.ui.hote, port=config.ui.port)`.
  `uvicorn` est réservé à `interfaces/cli.py` par `test_architecture.py` : cet import et l'appel
  `uvicorn.run` ne peuvent pas vivre dans `interfaces/web/`.
- Le registre des lots (`_RegistreLots`) est en mémoire, par instance d'application : un
  redémarrage du processus UI perd l'état des lots en cours (acceptable pour le POC, non
  testé ici).

## Revue

Détail : `_bmad-output/implementation-artifacts/revues/story-14.md`.

- medium, second avis : verrou non relâché sur multipart malformé — corrigé (`try/finally` jusqu'au démarrage du thread).
- medium, second avis : `Host: [::1]:<port>` refusé alors que `ui.hote = "::1"` est permis — corrigé ; **écart au §18** (hôte ajouté), à reporter dans contrats.md.
- low, second avis : noms réservés avec point ou espace (`CON.x.md`, `NUL .md`) — corrigé.
- low, second avis : lecture entière avant le contrôle de 1 Mo — corrigé (`read(1 Mo + 1)`).
- low, second avis : `testserver` en production — rejeté (imposé par §18).
- low, second avis : `Thread.start()` hors `try` — corrigé avec le premier constat.
- low, second avis : `.docx` absent d'un lot terminé -> 500 — corrigé (404) ; filtrage d'`id_lot` rejeté (borné par le registre).
- low, second avis : `POST` sans `Origin` accepté — rejeté (§18 ne vise que l'`Origin` présent).
- low, revue (complexité) : chaque interrogation renvoyait et redessinait tout le journal — corrigé (`?depuis=N` facultatif, JS incrémental).
- low, revue : interrogation sans fin d'un lot inconnu — corrigé (arrêt sur 404).
- low, revue : `erreur` peut contenir un chemin absolu — reporté (affichage local, hors contrat).
- Reporté, story 13 : commande `ui` (refus code 2 hors boucle locale, garde autour d'`uvicorn.run`) à vérifier à son intégration.

Tests : ciblés verts (`test_ui.py`, 16 avec `test_architecture.py`) ; suite complète 246 verts ;
`ruff check` et `ruff format --check` verts ; contrôle rapide vert. Aucune note écrite au disque
quand une note est refusée ou qu'un lot est déjà en cours.
