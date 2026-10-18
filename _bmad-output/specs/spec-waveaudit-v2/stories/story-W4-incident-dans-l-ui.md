---
id: W4
title: Workflow incident dans l'UI
status: review
sources:
  - ../stories.yaml
  - ../SPEC.md
  - ../formats.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/impacts-v2.md
  - ../../../planning-artifacts/ux/EXPERIENCE.md
  - ../../../planning-artifacts/ux/DESIGN.md
---

# Story W4 — Workflow incident dans l'UI

## Livré

- `interfaces/web/routeurs/incidents.py` (remplit le stub posé par W1) : `POST /incidents`
  dans le même ordre que `routeurs/lots.creer_lot` (revue W2) : occupation provisoire
  (`VerrouUnique.prendre(Occupation("incident", "", None, debut))`), validation des journaux,
  du modèle et de l'année, `nouvel_id_lot`, `definir`, écriture des journaux sous
  `var/entrees/<id>/`, `ecrire_fiche_lot(..., workflow="incident", langue=None)` avant le 303,
  arrêt du moteur (`run_in_threadpool`), fil `daemon` qui exécute `executer_incident` et libère
  le verrou en `finally` (log sur exception, comme W2). `GET /incidents/{id}` redirige (303) vers
  `/lots/{id}` si le lot est un lot de fiches (`lots.workflow_lot`), sinon rend `incident.html` ;
  `GET /incidents/{id}/etat` délègue à `lots_app.etat_lot` (même forme que les fiches) ;
  `GET /incidents/{id}/resultat` renvoie `{"id_lot","rapport","par_severite","total"}` (§26) ;
  `GET /incidents/{id}/rapport-incident.docx` sert le fichier une fois le lot terminé.
- Validation des journaux déposés : noms `^[A-Za-z0-9][A-Za-z0-9 ._-]{0,99}$`, refusés s'ils se
  terminent par `.` ou une espace, réservés Windows ou doublons (comparaison
  `rstrip(". ").casefold()`, comme les fiches) ; au plus 50 fichiers, 10 Mio chacun ; `400
  aucun_journal_reconnu` si aucun nom déposé n'est routé par `composition.journal_reconnu`
  (vérifié après les contrôles de nom et de taille, avant la création de l'identifiant de lot :
  aucun dossier n'est créé sur ce refus) ; `422 annee_invalide` hors de 1970–2100 ou non
  numérique, année courante par défaut.
- `application/composition.py` (ajout en fin de fichier) : `journal_reconnu(nom) -> bool`,
  nom public de `adaptateurs.journaux.router_journal` (import local dans la fonction, pour ne
  pas toucher le bloc d'imports du fichier — W4 et X2 s'y croisent, cf. commentaire d'en-tête de
  `stories.yaml`).
- `adaptateurs/journaux.py` : `_router` renommé `router_journal` (nom public, appelants internes
  alignés) ; aucun test n'importait `_router` (vérifié par `git grep`).
- `templates/incident.html` (nouveau) et `static/incident.js` (nouveau) : suivi (journal
  d'événements, comme `etat.js`) puis résultat une fois le lot terminé — tableau des détections,
  téléchargement direct du rapport (lien, comme `rapport.lot.docx`). Le filtre par sévérité
  (EXPERIENCE « Page incident ») est un groupe de 4 boutons bascule **rendus côté serveur** dans
  le gabarit (`role="group"`, `aria-label`, un bouton par sévérité avec `data-severite` et
  `aria-pressed="false"`) : les sévérités sont un ensemble fixe connu à l'avance, contrairement
  aux candidats ou aux entrées de relecture (dynamiques) — ce choix rend le filtre testable par
  une lecture simple du HTML rendu, sans exécution de JS, comme le reste de `tests/accessibilite.py`.
  Le JS met seulement à jour le texte (compte par sévérité) et l'état `aria-pressed` au clic.
- `static/style.css` (ajouts en fin de fichier) : `#resume` (disposition des boutons de filtre,
  état pressé) et `#detections` (tableau dense, DESIGN.md « Page incident »).

## Tests réalignés

- Aucun test existant ne touchait `routeurs/incidents.py` ni n'importait `adaptateurs.journaux._router`
  (vérifié par `git grep` avant le renommage, comme l'annonce `impacts-v2.md` ligne 29).
- Suite complète (`tests/unitaires`, `tests/e2e`) relancée une fois : 1003 tests verts, aucune
  régression sur `e2e/test_ui.py` ni `e2e/test_hors_ligne.py`.

## Tests nouveaux

- `e2e/test_incident_ui.py` (nouveau) : démo CERT (16 détections) créée par l'UI, comparée à la
  même commande CLI (`waveaudit incident`) sur le même dépôt et le même faux moteur — texte complet
  du `.docx` (paragraphes puis tableaux) identique entre les deux ; `par_severite` et `total`
  cohérents ; dépôt sans détection → `total == 0`, message statique « Aucune détection sur ce
  dépôt » présent dans la page, rapport quand même téléchargeable ; `aucun_journal_reconnu` sans
  aucun dossier créé (`var/entrees`, `var/sorties` inchangés) ; choix du modèle comme pour les
  fiches (modèle `externe` jamais repassé tel quel, `modele_indisponible` sur un nom inconnu) ;
  verrou partagé avec un lot de fiches en cours → `409 lot_en_cours` ; limites (nom terminé par
  `.` ou espace, plus de 50 fichiers, fichier de plus de 10 Mio) ; année hors 1970–2100 ou non
  numérique → `422 annee_invalide` ; `GET /incidents/{id}` d'un lot de fiches → 303 `/lots/{id}` ;
  `GET /incidents/{id}` juste après le 303 ne redirige pas vers `/lots` (lot.json écrit avant le
  303) ; `test_accessibilite_incident` (`tests/accessibilite.py`, rôles ARIA du filtre par
  sévérité et focus visible de `style.css`) ; cas hors ligne sous `garde(...)` avec
  `garde_reseau.tentatives() == []` pour un incident lancé via la commande `ui` (même motif que
  `e2e/test_hors_ligne.py::test_ui_lot_sous_garde_sans_tentative`, mais dans ce fichier, comme
  demandé par la story).

## Choix d'interprétation

- `composition.journal_reconnu` importe `adaptateurs.journaux.router_journal` **localement**
  dans la fonction plutôt qu'en tête de fichier : la story signale que W4 et X2 se croisent sur
  les ajouts de `composition.py`, et modifier le bloc d'imports (partagé) aurait un risque de
  conflit plus élevé qu'un ajout en fin de bloc de fonctions. `composition.py` reste réservé aux
  adaptateurs pour l'instanciation (`test_architecture.py`) ; cet import local ne fait qu'appeler
  une fonction pure, pas instancier un adaptateur, et ne change donc rien à ce contrat.
- Boutons de filtre par sévérité rendus côté serveur (statiques dans `incident.html`) plutôt que
  construits par `incident.js` au premier rendu : les 4 sévérités sont connues sans lecture du
  lot, ce qui permet de les tester par une lecture directe du HTML (comme le reste de
  `tests/accessibilite.py`, qui n'exécute aucun JS). Le JS ne fait que mettre à jour le texte
  (compte) et l'état `aria-pressed` des boutons déjà présents.
- Aucune page de dépôt dédiée au workflow incident (pas de `GET /incidents` sans identifiant) :
  le contrat §26 ne liste pas cette route, et le fichier `index.html`/`routeurs/pages.py` n'est
  pas dans le périmètre de cette story (`stories.yaml`, liste de fichiers de W4). Le dépôt se
  fait par `POST /incidents` directement (comme testé ici) ; l'intégration au sélecteur de
  workflow de l'accueil reste à faire par une story qui touche `index.html`/`pages.py` — reporté
  ci-dessous.

## Reports

- ~~Écran de dépôt du workflow incident sur l'accueil~~ : fait en revue (décision de
  l'orchestrateur), voir ci-dessous.

## Revue

Relue le 2026-10-18 (second avis Haiku puis reviewer Opus), détail dans
`_bmad-output/implementation-artifacts/revues/story-W4.md`.

- haute | second avis 1 | accueil sans choix fiches / incident ni formulaire vers `POST /incidents` (CAP-14 « Depuis l'accueil ») | corrigé : sélecteur `role="group"` à deux boutons `aria-pressed`, formulaire `#depot-incident` (journaux, modèle, année), `accueil.js` générique ; tests `e2e::test_accueil_formulaire_incident_aboutit_au_suivi`, `test_accueil_lot_en_cours_desactive_aussi_le_depot_incident`.
- faible | second avis 2 | import local de `router_journal` dans `composition.py` | rejeté : choix motivé (ajout seulement, X2 croise le bloc d'imports), sans effet.
- faible | second avis 3 | `afficherResultat` sans gestion d'erreur (409/404) | corrigé : message codé affiché, pas de section ni de lien vides.
- faible | second avis 4 | `/incidents/{id}/etat` sans contrôle de workflow | rejeté : §26 « forme de `/lots/{id}/etat` », champ `workflow` dans la réponse, `/lots/{id}/etat` symétrique sans contrôle ; la page redirige déjà.
- moyenne | reviewer | `annee="--5"` ou 5 000 chiffres : `int()` lève, réponse 500 au lieu de `422 annee_invalide` | corrigé : motif `-?[0-9]{1,6}` ; `test_annee_invalide` étendu.
- — | reviewer | Complexité : 0 constat nouveau (`/etat` relu à chaque sondage, hérité de §30, laissé comme en W2).
