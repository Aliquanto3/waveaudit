---
id: R2
title: Persistance de la relecture et fiche lot.json
status: review
sources:
  - ../stories.yaml
  - ../SPEC.md
  - ../formats.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/impacts-v2.md
---

# Story R2 — Persistance de la relecture et fiche lot.json

## Livré

- `application/relecture.py` (nouveau, contrats §25 « Persistance », AD-19) :
  - seul écrivain de `relecture.json` ; `_VERROUS` par chemin résolu (normcase), créé sous un
    verrou global ; chaque écriture lit, modifie, puis `ecrire_atomique` :
    `.relecture.json.partiel` puis `os.replace` retenté `ESSAIS_REMPLACEMENT = 10` fois à
    `PAUSE_REMPLACEMENT_S = 0.1` sur `PermissionError`, provisoire supprimé dans tous les cas ;
  - `initialiser`, `enregistrer_resultat` (fiche : candidats de la traçabilité,
    `candidat_choisi`, `a_valider`, `modele_generation = etat.modele` ; écartée : ses
    candidats) ;
  - `charger(dossier, *, occupation=None)` : `relecture.json`, sinon repli `fiches.json`
    v0.1.0 en mémoire (tri casefold, `source=None`, `modele` lu dans `lot_demarre`), sinon
    état vide si `lot.json` porte `workflow="fiches"`, sinon `RefusRelecture("lot_inconnu")` ;
    génération interrompue présentée à la lecture, sans écriture ;
  - `modifier(dossier, index, version_attendue, operation, *, occupation=None)`
    (`version_attendue=None` : sans contrôle, pour la régénération) ;
  - `demarrer_regeneration(..., *, ids_catalogue=(), occupation=None)` : refus dans l'ordre
    du §25 (`conflit_version`, `generation_en_cours`, `non_generable`, `source_absente`,
    `candidat_courant`, `candidat_inconnu`, `confirmation_requise`), puis `en_cours` ;
  - `regenerer(config, dossier, index, constat_id, moteur)` : modèle résolu du lot
    (`etat.modele` en local-gere, `etat.modele_demande` en externe), workflow construit avec la
    langue du lot, `remplacer_fiche(..., modele_generation=info.nom_modele)` ; `repli_moteur`
    → `echec` et fiche gardée ; toute exception → `echec` (`sans_chemin`), aucune exception ne
    sort, aucun événement ni `journal.jsonl`.
- `application/lot.py` : `config_pour_langue(config, langue)` (copie extraite, revue L1) ;
  `ecrire_fiche_lot(dossier, *, id_lot, workflow, langue, modele_demande)` (§30 : `cree_le`
  avec fuseau, `pid`, atomique, sans effet si présent) ; `executer_lot` écrit `lot.json` avant
  `composition.ouvrir`, `initialiser` après le tri, `enregistrer_resultat` avant l'événement de
  fin de fiche ; un `OSError` d'écriture de `relecture.json` donne `lot_echoue` avec
  `MESSAGE_ECRITURE_RELECTURE`, puis remonte.
- `application/incident.py` : `lot.json` (`workflow="incident"`, `langue=None`).

## Tests réalignés

- `e2e/test_incident.py::test_id_lot_fourni_et_sans_fichier_provisoire` : `lot.json` dans la
  liste exacte, contenu vérifié.
- `e2e/test_lot.py::test_lot_nominal_30_notes` : liste exacte des fichiers de sortie,
  `lot.json`, `relecture.json` (30 entrées dans l'ordre des événements, version 2).

## Tests nouveaux

- `u/test_relecture.py` (26) : tous ceux nommés par la story, plus `conflit_version` /
  `entree_inconnue`, `modifier` sans effet, `os.replace` simulé en échec (10 essais),
  confirmation d'une fiche corrigée, régénération dans la langue du lot, toute exception →
  `echec`.
- `e2e/test_lot.py` : `test_lot_echoue_au_milieu_entrees_attente`,
  `test_lot_echoue_si_relecture_verrouillee`.

## Choix d'interprétation

- `modifier` n'écrit ni n'incrémente quand `operation(entree) == entree` (consigne de revue
  R1 ; le §25 ne cite pas l'exception).
- Réessais : 10 × 100 ms (contrats §25 [revue A11/E14]) et non 5 × 50 ms (texte « Fichiers »
  de la story, antérieur à la revue).
- `demarrer_regeneration` reçoit `ids_catalogue` (absent de la signature du §25) : seul
  contrôle d'existence pour `non_rattachee` ; vide → `candidat_inconnu`. La route (W3a) passe
  les ids du catalogue.
- `demarrer_regeneration` n'a pas de paramètre `occupation` (signature du §25, revue R2) : la
  route prend le verrou pour cette entrée avant l'appel, une entrée `en_cours` lue alors est
  forcément interrompue et relançable ; `generation_en_cours` est tenu par le verrou (409
  `lot_en_cours`). Les routes de correction et validation passent l'occupation courante à
  `modifier` et `charger`.
- `executer_lot` refuse (`EntreeInvalide`, « lot déjà exécuté ») un `id_lot` fourni dont le
  dossier porte déjà `relecture.json` ou `journal.jsonl` (§25 « Relance », revue R2).
- La lecture sous verrou de `modifier` ne présente que l'entrée visée : une autre entrée
  `en_cours` n'est jamais réécrite en `echec`.
- `enregistrer_resultat` remet à zéro les champs incompatibles avec le résultat (correction,
  génération), ce qui ne change rien dans le lot (entrées `attente`).
- « Lot échoué au milieu » : simulé par un `traiter` qui lève `MoteurInjoignable` à la 3e note ;
  un faux moteur réellement coupé donne des fiches de repli, pas un échec de lot.

## Reports

- Routes de relecture et passage de `ids_catalogue`, `occupation`, verrou et 503
  `ecriture_impossible` : W3a. Lecture de `lot.json` pour l'état des lots : W2 (`lots.py`).

## Revue

Revue unique (reviewer, avec le second avis) : `_bmad-output/implementation-artifacts/revues/story-R2.md`.

- moyenne | second avis 1 | corrigé | `occupation` de `demarrer_regeneration` retiré : la passer après `prendre` bloquait à jamais une entrée interrompue.
- moyenne | second avis 3 | corrigé | `id_lot` fourni déjà exécuté refusé avant toute écriture.
- moyenne→faible | second avis 2 | rejeté | écritures d'un autre processus exclues par le contrat (`lot_en_cours_externe`, SPEC l. 87) ; nom `.relecture.json.partiel` fixé par §30.
- faible | second avis 4 | reporté | `relecture.json` illisible : `ValidationError` (`ValueError`) ; code d'API à arbitrer (W3a).
- faible | second avis 6 | corrigé | suppression du provisoire en échec journalisée, l'erreur d'origine remonte.
- faible | second avis 5, 7, 8, 9 | rejetés ou reportés | voir la revue.
- Complexité : 1 constat | réécriture complète par fiche (O(n²) par lot) : 18 ms/fiche à 300 notes, négligeable devant la génération ; laissé.
