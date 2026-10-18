---
id: W2
title: Accueil v2, lots récents et suivi lu sur le disque
status: review
sources:
  - ../stories.yaml
  - ../SPEC.md
  - ../formats.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/impacts-v2.md
  - ../../../planning-artifacts/ux/EXPERIENCE.md
---

# Story W2 — Accueil v2, lots récents et suivi lu sur le disque

## Livré

- `application/lots.py` (nouveau, lecture seule, contrats §30) : `ResumeLot` (dataclass figée,
  `externe: bool` en plus des champs du contrat) ; `lister_lots(config, occupation)` (tri
  `cree_le` puis `id_lot` décroissants, au plus 50) ; `etat_lot(config, id_lot, occupation,
  depuis=0)` (forme de `GET /lots/{id}/etat`, `workflow` compris). Source : `journal.jsonl` et
  `lot.json` relus à chaque appel ; ligne de journal illisible ignorée (log) ; workflow déduit
  de `lot.json`, sinon de `incident.json`/`rapport-incident.docx` (lot v0.1.0), sinon `fiches` ;
  `en_cours` si l'occupation courante porte ce lot, ou si `lot.json.pid` est vivant dans un
  autre processus (`composition.processus_actif`) sans événement de fin ; `interrompu` sinon.
- `application/composition.py` (ajout en fin de fichier) : `ModeleInstalle` et
  `modeles_installes(config)` (§11 : en `local-gere`, artefacts `modele_defaut`/`modele_repli`/
  `candidat` dont le fichier existe, dans l'ordre du manifeste, `defaut` sur le choix de
  `choisir_modele` s'il est installé sinon le premier installé ; en `externe`, une seule entrée
  `modele_api or "externe"`, rôle `externe`) ; `processus_actif(pid, cree_le)`.
- `adaptateurs/memoire_psutil.py` : `date_creation_processus(pid)` (écart signalé ci-dessous).
- `interfaces/web/app.py` : `creer_app` crée `app.state.config`, `VerrouUnique` et
  `MoteurALaDemande` (§24) ; `app.state.lots` (registre en mémoire v0.1.0) supprimé ; lifespan
  FastAPI qui attend la libération du verrou 10 s au plus puis ferme le moteur (`[revue E3]`).
- `interfaces/web/routeurs/lots.py` : `POST /lots` dans l'ordre du §26 (occupation provisoire,
  validation, `nouvel_id_lot`, `definir`, écriture des notes, `lot.ecrire_fiche_lot` avant le
  303, `MoteurALaDemande.fermer()`, fil `daemon`) ; refus après l'identifiant obtenu supprime
  `var/entrees/<id>/` et `var/sorties/<id>/` ; modèle et langue facultatifs validés
  (`modele_indisponible`, `langue_invalide`), le modèle `externe` affiché n'est jamais repassé
  tel quel (`None`) ; 409 `lot_en_cours` porte `occupation` ; `GET /lots/{id}/etat`,
  `GET /lots/{id}/rapport.docx`, `GET /api/lots`, `GET /api/modeles` lisent `application/lots.py`
  et `composition.modeles_installes`.
- `interfaces/web/routeurs/pages.py` : `GET /` passe les modèles installés, la langue par
  défaut, l'occupation courante et la présence d'au moins un lot ; nouveau `GET /lots` (lots
  récents) ; `GET /lots/{id}` répond 404 `lot_inconnu` via `dossier_lot_existant` (aucun GET
  n'écrit sur le disque).
- `templates/index.html` (modèle, langue, bandeau d'occupation, lien « Lots récents »
  conditionnel), `templates/lots.html` (nouveau), `static/etat.js` (état `interrompu` traité
  comme `echoue`, EXPERIENCE « State Patterns »).

## Tests réalignés

- `e2e/test_ui.py::test_bandeau_sur_chaque_page` (`GET /lots/un-identifiant` → 404 ; bandeau
  vérifié sur un lot réellement créé), `::test_pages_portent_le_jeton_sans_script_ni_style_en_ligne`
  (même lot réel), `::test_second_envoi_pendant_un_lot_refuse_sans_ecriture` (409 avec
  `occupation`).
- `::test_rapport_avant_la_fin_et_lot_inconnu`, `::test_etat_depuis_ne_renvoie_que_les_nouveaux_evenements`,
  `::test_lot_nominal_20_notes_puis_telechargement` : verts sans changement (lecture disque déjà
  compatible).
- `e2e/test_hors_ligne.py::test_ui_lot_sous_garde_sans_tentative` : vert sans changement.

## Tests nouveaux

- `u/test_modeles_installes.py` (nouveau fichier, pas `u/test_composition.py`) : manifeste
  fabriqué sous `tmp_path`, fichiers présents/absents, défaut, repli si RAM basse, aucun
  installé, externe une entrée, `processus_actif` (pid mort, vivant avant/après `cree_le`).
- `u/test_lots.py` : workflow et état selon `lot.json`/journal/occupation, lot v0.1.0 sans
  `lot.json`, ligne illisible ignorée, pid vivant d'un autre processus → `en_cours` et
  `externe`, pid mort → `interrompu`, tri par `cree_le`.
- `e2e/test_ui.py` : `GET /lots/inconnu` ne crée aucun dossier ; `GET /lots/{id}` juste après le
  303 → page de suivi ; `test_accessibilite_lots_et_suivi` ; `/api/modeles` (défaut
  présélectionné) ; modèle et langue reçus par le lot (faux moteur : `model`, consigne anglaise)
  ; 422 `modele_indisponible` et `langue_invalide` ; `/api/lots` (fiches et incident
  `interrompu`) ; relance = nouveau lot ; lien « Lots récents » absent sans lot.

## Choix d'interprétation

- `composition.py` ne peut pas importer `psutil` directement (réservé aux adaptateurs,
  `test_architecture.py::test_bibliotheques_reservees`) : `processus_actif` délègue à
  `adaptateurs/memoire_psutil.date_creation_processus(pid)`, nouvelle fonction minimale dans un
  fichier non listé par la story mais nécessaire pour respecter cette règle.
- Le lifespan attend la libération du `VerrouUnique` (pas un compteur interne de
  `MoteurALaDemande`, qui n'est pas exposé publiquement et que la story ne permet pas de
  modifier) : une occupation en cours (lot ou régénération) retarde la fermeture du moteur,
  jusqu'à 10 s.
- `409 lot_en_cours` porte `occupation` sous la forme `{"nature", "id_lot", "debut"}` (le
  contrat ne fixe pas la forme exacte, seulement le champ).

## Reports

- Redirection 303 entre `/lots/{id}` et `/incidents/{id}` (§26) : non implémentée, car
  `routeurs/incidents.py` reste un stub (W4) et aucun lot incident ne peut être créé avant
  cette story ; à faire avec W4, quand `GET /incidents/{id}` existera.
- Workflow incident dans l'UI (dépôt, modèle, année) : W4.

## Revue

En attente (second avis puis reviewer).
