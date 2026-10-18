---
id: X2
title: Service d'export et commande waveaudit exporter
status: review
sources:
  - ../stories.yaml
  - ../SPEC.md
  - ../formats.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/impacts-v2.md
---

# Story X2 — Service d'export et commande `waveaudit exporter`

## Livré

- `application/export.py` (nouveau, contrats §27, CAP-13, CAP-17, AD-19) :
  - `exporter_lot(config, id_lot, mode) -> tuple[Path, int]` : `dossier_lot_existant` (sinon
    `RefusRelecture("lot_inconnu")`) ; état lu par `lots.etat_lot(config, id_lot, None)`
    (sinon `lot_inconnu`) ; `workflow == "incident"` → `RefusRelecture("lot_incident")`
    (couvre aussi un lot incident v0.1.0 sans `lot.json`, reconnu par `incident.json`) ;
    `etat == "en_cours"` → `RefusRelecture("lot_en_cours")` ; `relecture.charger(dossier)`
    puis `rapport_export(etat, mode)` ; en mode `final`, aucune fiche →
    `RefusRelecture("aucune_fiche_validee")` ; export via
    `composition.creer_exporteur(config).exporter(...)`, sous un verrou par chemin cible
    résolu (`threading.Lock`, `_VERROUS` indexé par `os.path.normcase`, même schéma que
    `application/relecture._verrou`) ;
  - Renvoie `(chemin, nombre de fiches non validées)`. `chemin` =
    `var/sorties/<id>/rapport-<id>.docx` ou `brouillon-<id>.docx`, écrasé à chaque export
    (l'exporteur écrit déjà dans un provisoire nommé par uuid avant `os.replace`, §17/§27 ;
    le verrou du service est une garantie supplémentaire).
- `application/composition.py` : `creer_exporteur(config) -> ExportDocx` (ajout en fin de
  fichier, seul point d'instanciation de l'exporteur hors `ouvrir`).
- `interfaces/cli.py` : commande `exporter LOT [--brouillon] [--config F]` (ajout en fin de
  fichier, avant `sbom`) : bandeau en première ligne, puis sous `garde(...)`, codes retour via
  `_codes_retour("exporter")` (0 ; 2 pour `lot_inconnu`, `lot_incident`, `lot_en_cours`,
  `aucune_fiche_validee`, `ConfigurationInvalide` ; 4 pour `PermissionError` et le reste) ;
  succès : `rapport : <nom> (lot <id>)`, puis en mode final si `n > 0` une ligne
  `fiches non validées : <n> (exclues, listées en annexe)`, puis le bandeau. Aucune validation
  de fiche.

## Tests réalignés

- `u/test_composition.py::test_ouvrir_moteur_incident_sans_port_des_fiches` : inchangé, resté
  vert sans modification (le workflow incident n'appelle jamais `creer_exporteur`).

## Tests nouveaux

- `u/test_export.py` : `lot_inconnu`, `lot_incident`, `lot_incident` v0.1.0 sans `lot.json`,
  `lot_en_cours` (pid vivant simulé d'un autre processus), `aucune_fiche_validee`, final avec
  fiche validée dans sa version corrigée (libellés et marque absents), brouillon avec marque
  et langue du lot (libellés anglais), écrasement à chaque export, nombre de non validées
  renvoyé (mixte validée/non validée), aucun `.partiel` restant, deux exports simultanés
  (4 fils) sans mélange ni résidu.
- `e2e/test_cli.py` : `exporter` — codes 0 (final avec fiche validée), 2 (lot inconnu,
  incident, en cours, aucune validée), 4 (fichier cible verrouillé, simulé par un dossier à la
  place du `.docx` : `os.replace` lève `PermissionError` sous Windows comme un document ouvert
  dans Word) ; bandeau en première et dernière ligne ; `--brouillon` sans la ligne « fiches non
  validées » (réservée au mode final) ; ligne « fiches non validées : n » en final mixte ;
  aucune fiche validée après un export (la commande ne valide rien).

## Choix d'interprétation

- `lots.etat_lot(config, id_lot, None)` est appelé avec `occupation=None` (consigne héritée de
  R2/W2) : l'export tourne dans son propre processus (CLI, ou future route W3a sans verrou de
  régénération), jamais sous l'`Occupation` d'un lot en cours de génération dans ce même
  processus.
- Le verrou par chemin du service (`_VERROUS` dans `application/export.py`) est distinct de
  celui de `application/relecture.py` (fichiers différents, `relecture.json` contre
  `rapport-<id>.docx` / `brouillon-<id>.docx`) : pas de réutilisation du verrou de relecture,
  pour ne pas bloquer un export derrière une écriture de relecture sans rapport.
- `dossier_lot_existant` est la seule entrée de lecture du dossier (jamais `verifier_id_lot`,
  qui crée un dossier) : un export sur un lot inconnu ne crée jamais `var/sorties/<id>/`.

## Reports

- Route web `POST /lots/{id}/export` (contrats §26 : `GET /api/lots`) : W3a, qui réutilisera
  `application.export.exporter_lot` en lui passant `occupation=verrou.occupation()` (mêmes
  codes `RefusRelecture`, traduits en 404/409 par la route ; voir `revues/story-X2.md`).

## Revue

Détail : `_bmad-output/implementation-artifacts/revues/story-X2.md`.

- moyenne, second avis 1, corrigé : §27 étape 3 (verrou de ce processus) non couvert ;
  `exporter_lot(..., *, occupation=None)` passé à `etat_lot` et `charger`, refus `lot_en_cours`
  si l'occupation porte ce lot.
- faible, second avis 2, rejeté : `generation` non lue par `rapport_export`, docx inchangé.
- faible, second avis 3, rejeté : `_VERROUS` borné par le nombre de lots.
- faible, second avis 4, corrigé : test renommé `test_exporter_final_sans_fiche_validee_code_2`.
- faible, reviewer, corrigé : message `PermissionError` « fermez le document dans Word » (§27).
- Complexité : 0 constat.
