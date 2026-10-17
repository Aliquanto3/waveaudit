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

- Point final collé à un jeton (motifs normatifs, `(?![\d.])`, comportement figé par
  `test_motifs_point_final_comportement_fige`) : `MOTIF_TECHNIQUE` sur « T9999. » ou
  « T1110.001. » → aucun jeton ; `MOTIF_IPV4` sur « 203.0.113.254. » → aucun jeton ;
  `MOTIF_IPV6` sur « 2001:db8::1. » → candidat `2001:db8::1.` invalide pour `ipaddress`,
  donc « laissé tel quel » par §21 garde-fous étape 3. Conséquence : une technique, une IPv4
  ou une IPv6 inventée en fin de phrase survit aux garde-fous (trou CAP-5). §21 ne décrit
  aucun retrait de ponctuation pour ces jetons (seul §6 MVP le fait, pour les URL).
  À faire en C4, après décision consignée dans contrats §21 : passer les motifs sur une
  copie du texte où chaque « . » suivi d'un blanc ou de la fin du texte est remplacé par
  une espace (même longueur, donc positions inchangées pour le retrait dans le texte
  d'origine) ; tests C4 obligatoires : « T9999. », « 203.0.113.254. », « 2001:db8::1. »
  retirés ; « T1110.001. » gardé si la règle l'a ; vecteurs de non-mutilation inchangés
  (`10.0.17763.1`, `08:02:10`…). Si l'orchestrateur refuse l'écart, C4 applique les motifs
  tels quels et le trou est consigné comme limite connue.

## Revue

- medium — second avis — reporté (C4) : motifs normatifs ratant un jeton suivi d'un point
  final ; motifs non modifiés (contrat), comportement figé par un test, traitement C4
  décrit ci-dessus.
- info — reviewer — vérifié : `JournalLot` sûr en cas d'exception (fichier fermé par
  `__exit__`, exception propagée, `lot_echoue` écrit avant fermeture comme avant).
- info — reviewer — vérifié : faux moteur incident (`<constat>` prioritaire, `<regle>`
  ensuite, `SANS_CONSTAT` sinon ; scénarios d'erreur traités avant, donc valables en mode
  incident).
- low — reviewer — rejeté : `decalage_syslog` accepte `+99:99` (motif du contrat seul) ;
  C2 échouera au calcul du fuseau, hors périmètre C1.
- Complexité : 0 constat (journal en ajout O(1) par événement).
