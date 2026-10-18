---
id: W1
title: Socle web (routeurs, CSRF, en-têtes de sécurité, erreurs codées)
status: review
sources:
  - ../stories.yaml
  - ../SPEC.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/impacts-v2.md
---

# Story W1 — Socle web

## Livré

- `interfaces/web/app.py` : `creer_app(config, *, hotes_test=())` crée le jeton CSRF
  (`app.state.jeton_csrf`), pose le middleware commun dans l'ordre du §26 (Host comparé en
  minuscules, sans port si le port vaut 80 ; Origin ; `X-CSRF-Token` par
  `secrets.compare_digest` ; `Content-Length` absent → 411, au-delà de 20 Mio (`/lots`),
  50 Mio (`/incidents`) ou 256 Kio → 413 `limite: "total"`), ajoute CSP, `nosniff`,
  `no-referrer` à toute réponse et `Cache-Control: no-store` hors `/static/`, et inclut les
  cinq routeurs. Erreurs HTTP et de validation converties en `{detail, code}`.
- `interfaces/web/routeurs/` : `pages` (`/`, `/lots/{id}`, `GET /api/jeton`), `lots`
  (routes v0.1.0, `_RegistreLots` conservé jusqu'à W2), `relecture`, `incidents`, `theme`
  vides. `interfaces/web/commun.py` : bandeau, gabarits, `page()` (passe `jeton_csrf`),
  `erreur()`, `en_mo()`.
- `POST /lots` : codes `lot_en_cours`, `nom_refuse`, `aucune_note`, `trop_de_fichiers` (plus
  de 100), `trop_volumineux` `limite: "fichier"`, `corps_invalide` (multipart illisible) ;
  noms terminés par `.` ou espace refusés, doublons après `rstrip(". ").casefold()` ;
  messages de Voice and Tone. Message d'échec du lot passé par `sans_chemin`.
- Gabarits : `<meta name="csrf">` dans `base.html` ; `static/commun.js` (`WaveAudit.envoyer` :
  jeton sur chaque écriture, relecture de `/api/jeton` et rejeu une fois sur 403
  `csrf_invalide`, message de redémarrage au second refus) ; `static/accueil.js` (dépôt par
  `fetch`). Aucun script ni style en ligne.
- `tests/web_outils.py` : `client(config)` (avec `hotes_test=("testserver",)`) ou
  `client(app, base_url=...)`, jeton CSRF posé sur chaque requête.
- Tests réalignés : tous les `POST` de `e2e/test_ui.py` passent par `web_outils`, codes
  vérifiés ; le cas « trop gros » de `::test_noms_refuses` devient 413 `limite: "fichier"`
  (dans `::test_limite_par_fichier_et_totale`) ; `e2e/test_hors_ligne.py::test_ui_lot_sous_garde_sans_tentative`
  (application réelle de `ui`, Host `127.0.0.1:<port>`).
- Tests nouveaux (`e2e/test_ui.py`) : 403 sans jeton, mauvais jeton, jeton d'une autre
  instance ; 411 ; 413 fichier, total et 256 Kio ; `trop_de_fichiers` ; noms en `.`/espace ;
  doublons normalisés ; `aucune_note` ; `testserver` refusé sans `hotes_test` ; Host en
  capitales ; `/api/jeton` ; méta CSRF, aucun script, `on*=` ni `style=` ; CSP, `nosniff`,
  `no-referrer` et `no-store` sur chaque réponse (refus du middleware compris) ; corps
  d'erreur codés sans chemin absolu.

## Choix d'interprétation

- Codes absents de la table du §26, posés pour tenir « toute erreur JSON a un `code` » :
  `introuvable` (404 hors routes, rapport absent d'un lot terminé), `methode_refusee` (405),
  `requete_invalide` (422 de validation FastAPI, ex. `depuis=-1`), `erreur_http` (autres
  statuts). `corps_invalide` (code du §26) réutilisé pour un multipart illisible.
- `nom_refuse` : message de Voice and Tone pour un nom invalide ; nom réservé Windows et
  doublon ont leur propre phrase, même code.
- 409 `lot_en_cours` : heure de prise du verrou dans le message ; le champ `occupation` vient
  avec `VerrouUnique` (W2).
- `Cache-Control: no-store` posé sur toutes les réponses hors `/static/` (docx compris), plus
  large que « JSON et HTML ».
- Plus de 1000 fichiers : rejet par l'analyseur multipart de Starlette, rendu en
  `trop_de_fichiers` sans le compte exact.

## Reports

- `VerrouUnique`, `MoteurALaDemande`, lifespan `fermer()`, état lu sur disque, `occupation`
  du 409, modèle et langue : W2.
- Aide `tests/accessibilite.py` : W5.
- Un nom envoyé par le client avec un chemin Windows (`C:\…\x.md`) n'est pas testable par
  `httpx` (il ne garde que le nom de base) : non couvert.
