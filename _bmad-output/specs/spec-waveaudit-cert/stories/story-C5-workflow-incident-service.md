---
id: C5
title: Workflow incident, service et calibrage
status: review
sources:
  - ../stories.yaml
  - ../SPEC.md
  - ../formats-incident.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
---

# Story C5 — Workflow incident, service et calibrage

## Livré

- `src/waveaudit/workflows/incident/prompt.py` : `construire(regle, detection,
  prefixe_systeme, max_preuves) -> [system, user]`. Système = `prefixe_systeme` + `\n` +
  `CONSIGNE` (consigne seule si le préfixe est vide). User = `<regle>` + JSON `{id, titre,
  description, impact, recommandation}` (`ensure_ascii=False`) + `</regle>\n<preuves>\n` +
  au plus `max_preuves` lignes `ligne_preuve(e)` (premiers événements de la détection) +
  `\n</preuves>`. Ni sévérité ni références dans le prompt.
- `src/waveaudit/workflows/incident/pipeline.py` : `traiter_detection(detection, regle,
  moteur, prefixe_systeme, config) -> Recit` (indicateurs par `model_copy` +
  `extraire`, `generer_json(messages, schema_recit(longueur_max_recit),
  max_tokens=incident.max_tokens)`, `appliquer_recit`) ; `SortieInvalide` → un nouvel
  essai avec les mêmes messages puis repli `repli_sortie_invalide` ; `MoteurInjoignable`
  (y compris HTTP 500) → repli immédiat `repli_moteur`. `sortie_de_repli(regle)`.
  `assembler_rapport(lecture, recits, regles)` selon §21 ; union dédoublonnée par
  `Evenement.cle` (seul endroit du dédoublonnage) ; `actifs` triés par
  `(casefold, graphie)` pour un ordre total.
- `src/waveaudit/application/incident.py` : `executer_incident(requete, config,
  abonne=None) -> ResultatIncident`. Dossier absent → `EntreeInvalide` avant création du
  lot ; `nouvel_id_lot` (ou `id_lot` fourni, mêmes vérifications que `lot.py`) ;
  `creer_ports_incident`, lecture, `detecter` ; moteur ouvert et sondé seulement s'il y a
  une détection. Journal par `JournalLot` (émetteur `_Emetteur` de `lot.py` réutilisé) :
  `lot_demarre` (`total` = détections, `details = {"workflow": "incident"}`, plus
  `pid_moteur` quand le moteur est ouvert), `fiche_demarree`/`fiche_terminee` par
  détection (`note = regle_id`, `statut`, `duree_s`), `lot_termine` (`id_lot`,
  `workflow`, `detections`, `rapport`), `lot_echoue` sur toute erreur sortante (message
  sans chemin absolu). `incident.json` = `model_dump_json(indent=2)` en UTF-8 (octets,
  LF) et `rapport-incident.docx` dans `var/sorties/<id_lot>/`, copie vers
  `copie_rapport`.
- `application/composition.py` : ajout de `creer_ports_incident(config)` seulement
  (`SourceJournauxFichiers(incident.decalage_syslog)`,
  `CatalogueReglesYaml(chemins.regles)`, `ExporteurIncidentDocx(chemins.theme_prive,
  max_preuves=incident.max_preuves)`), plus les imports correspondants.
- Tests : `tests/unitaires/test_prompt_incident.py`, `test_pipeline_incident.py`
  (faux moteur : nominal, `references_inventees`, `json_invalide_une_fois`,
  `json_invalide`, `erreur_500`, `injoignable` ; assemblage) ; `tests/e2e/test_incident.py`
  (démo = oracle pour détections, indicateurs et ignorées, part bénigne ≥ 0,60, 80
  événements lus ou plus, `incident.json` valide, journal, < 30 s ; déterminisme ;
  scénarios d'échec ; sans détection avec moteur injoignable et ouverture interdite ;
  démo avec moteur injoignable → `MoteurInjoignable` et `lot_echoue` ; dossier absent ou
  sans fichier routé → `EntreeInvalide`).

## Calibrage

Aucun écart : sortie du service, oracle `donnees/demo/incident-attendu.yaml`, règles et
démo concordent sans modification (16 détections, 16 indicateurs, ignorées, part
bénigne). Ni l'oracle, ni les règles, ni la démo ne sont modifiés.

## Écarts au contrat

- `assembler_rapport(lecture, recits, regles)` : troisième argument (règles par id), car
  la recommandation **type** de chaque règle n'est pas portée par `Recit` (seule la
  recommandation adaptée l'est). Signature §21 : `assembler_rapport(lecture, recits)`.
- `application/incident.py` importe des noms privés de `lot.py` (`_Emetteur`,
  `_sans_chemin`, `_ID_LOT`, `_sorties`) pour réutiliser sans dupliquer (AD-17) ; `lot.py`
  n'est pas modifié.
- `lot_demarre.details` porte `pid_moteur` (valeur `None` en mode externe) seulement quand
  le moteur est ouvert ; sans détection, `{"workflow": "incident"}` seul.
- Sortie de moteur sans une rubrique : pas de `SortieInvalide` ajoutée (le contrat ne le
  prévoit pas) ; les garde-fous complètent la rubrique (`rubrique_completee`).

## Reports (C6b)

- Commande `waveaudit incident` : appeler `executer_incident` sous le garde réseau,
  convertir `PermissionError` (export ou copie `-o`) en code 4, codes 2/3 comme `fiches`.
- README : limites connues (§21), script PowerShell d'export.
