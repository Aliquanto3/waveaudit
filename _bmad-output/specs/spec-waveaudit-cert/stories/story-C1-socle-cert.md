---
id: C1
title: Extension du socle pour le CERT
status: review
sources:
  - ../stories.yaml
  - ../SPEC.md
  - ../formats-incident.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
---

# Story C1 — Extension du socle pour le CERT

## Livré

- `src/waveaudit/domaine/incident.py` (nouveau) : formes de §21 (`Evenement` avec `cle`, non
  hachable ; `LigneIgnoree`, `LectureJournaux`, `Condition` avec `au_moins_un`, `Agregation`,
  `Regle`, `Indicateur`, `Detection`, `Recit` avec `regle_titre`, `RapportIncident`,
  `RequeteIncident`, `ResultatIncident`), toutes `extra="forbid", frozen=True`, avec les
  validations du tableau §21 ; `schema_recit` ; constantes `CHAMPS_WINDOWS` (23 clés),
  `CHAMPS_LINUX`, `PROGRAMMES_LINUX`, `SEVERITES`, `LIBELLES_SEVERITE`, `TYPES_INDICATEUR`,
  `IDS_REGLES_MINIMAUX`, `MOTIF_TECHNIQUE`, `MOTIF_IPV4`, `MOTIF_IPV6`, `MOTIF_HACHAGE`
  (motifs compilés).
- Socle MVP, ajouts seulement : `domaine/modeles.py` (`CodeMotif.INDICATEUR_RETIRE`),
  `domaine/ports.py` (`SourceJournaux`, `CatalogueRegles`, `ExporteurIncident`,
  `PortsIncident` sans moteur), `domaine/configuration.py` et `config/waveaudit.toml`
  (`chemins.regles`, section `[incident]` bornée). `application/config.py` inchangé.
- Deux extractions sans changement de comportement : `application/journal.py`
  (`JournalLot`, désormais utilisé par `lot.py`, mêmes ouverture en ajout UTF-8, ligne et
  flush) et `composition._ouvrir_moteur`, partagée par `ouvrir` (inchangé) et
  `ouvrir_moteur_incident` (moteur, préfixe système, info ; aucun port des fiches).
- `tests/faux_moteur.py` : mode incident (`<regle>` sans `<constat>`), scénarios
  `nominal`, `references_inventees` (`REFERENCES_INVENTEES_INCIDENT`), `vecteur_invalide`
  = nominal ; `SCENARIOS` inchangé.
- `tests/incident_outils.py` : fabriques `evenement`, `regle`, `detection`, `recit`.
- `tests/donnees/incident/canoniques.yaml` : 34 entrées (17 chronologie, 11 bénignes,
  6 normalisations : entiers JSON, cellules CSV vides, IPv4 mappée verbatim, null/blanc/
  booléen/objet, CSV `;`, syslog ISO 8601). Lecture et conditions vérifiées hors dépôt par un
  lecteur et un évaluateur jetables, écrits d'après formats-incident.md.
- `donnees/regles/.gitkeep`, `donnees/demo/incident/.gitkeep`.
- Tests : `test_incident_modeles.py`, `test_canoniques.py`, `test_journal.py`, ajouts à
  `test_config.py`, `test_faux_moteur.py`, `test_composition.py` (cas existants inchangés).

## Écarts au contrat

- `ouvrir_moteur_incident(config, modele, *, id_lot=None)` : argument nommé facultatif en
  plus, comme `ouvrir`, pour nommer le journal `llama-server-<id_lot>.log` (C5 peut l'ignorer).

## Reports

- `MOTIF_IPV4` (normatif) ne reconnaît pas une IP suivie d'un point final
  (« … depuis 192.0.2.10. ») à cause de `(?![\d.])` : une IP inventée en fin de phrase ne
  serait pas retirée par les garde-fous (C4). À trancher par mise à jour de contrats §21.
