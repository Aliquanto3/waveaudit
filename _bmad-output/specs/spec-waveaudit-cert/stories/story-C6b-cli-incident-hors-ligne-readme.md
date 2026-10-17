---
id: C6b
title: CLI incident, preuve hors ligne et documentation
status: review
sources:
  - ../stories.yaml
  - ../SPEC.md
  - ../formats-incident.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
---

# Story C6b — CLI incident, preuve hors ligne et documentation

## Livré

- `src/waveaudit/interfaces/cli.py` : commande `incident DOSSIER [-o FICHIER] [--annee N]
  [--modele NOM] [--config F]`, calquée sur `fiches` (chargement de la configuration,
  `with garde(cfg.reseau.hotes_autorises):`, bandeau en tête et en pied, résumé console
  « N récit(s) ok, M à revoir ; rapport : … »). `--annee` vaut l'année courante par défaut
  (`datetime.now().year`), jamais exercé dans les tests (toujours `--annee 2026`). L'abonné
  console n'affiche que `FICHE_TERMINEE` (seul type émis par détection dans le workflow
  incident, contrats §21 « Service »). Codes retour identiques à `fiches` via `_codes_retour`
  (déjà en place) : 0 nominal ou sans détection même moteur injoignable, 2 `EntreeInvalide`/
  `ConfigurationInvalide` (dossier absent, vide ou sans fichier routé), 3 `MoteurInjoignable`
  (sonde, seulement s'il y a au moins une détection), 4 `PermissionError` (`-o` verrouillé).
  Aucune autre commande modifiée.
- `src/waveaudit/interfaces/cli.py`, `_codes_retour` : les messages d'`EntreeInvalide` et de
  `ConfigurationInvalide` passent désormais par `_sans_chemin` avant affichage (comme la
  branche `Exception` générique), import hissé en tête de fonction. Ce nettoyage couvre aussi
  `fiches`, qui lève le même genre de message (« dossier introuvable (chemin) ») sans jamais
  avoir été testé pour l'absence de chemin absolu en sortie CLI.
- `tests/e2e/test_cli_incident.py` (nouveau) : nominal sur le jeu de démonstration
  `donnees/demo/incident/` (bandeau, 16 lignes de récit, code 0), dossier absent (code 2, sans
  chemin absolu dans la sortie), dossier vide (code 2), moteur injoignable sur la démo
  (code 3), moteur injoignable sur un dossier sans détection (code 0), `-o` vers un dossier
  existant → `PermissionError` → code 4 (sans chemin absolu), et `--modele` répercuté dans
  `journal.jsonl`.
- `tests/e2e/test_hors_ligne.py` : `test_cli_incident_sous_garde_sans_tentative` (nominal sous
  garde, `garde_reseau.tentatives() == []`), à l'image de `test_cli_lot_sous_garde_sans_tentative`.
- `README.md` : section « Utilisation — CERT (analyse d'incident) » (usage, sorties, jeu de
  démonstration, limites connues du contrats §21 : décalage horaire fixe, export Windows
  PowerShell au format normalisé, motifs à point final neutralisés et IPv6 en prose abrégée
  retirées des indicateurs, absence de coupe-circuit moteur, lecture des journaux non en flux),
  commande `incident` ajoutée au tableau des commandes et à la liste des commandes sous garde
  (preuve hors ligne). Badge CI et reste du fichier inchangés.

## Écarts au contrat

- Aucun.

## Reports

- `_codes_retour` nettoyait déjà le chemin pour la branche `Exception` générique mais pas pour
  `EntreeInvalide`/`ConfigurationInvalide` ; le correctif touche aussi `fiches` (fichier
  partagé, contrats §19). Aucun test de `fiches` ne vérifiait l'absence de chemin absolu pour
  ce cas avant cette story ; à couvrir explicitement pour `fiches` si une revue future le juge
  nécessaire (hors périmètre de C6b).

## Revue

Branche `story-C6b-revue` (depuis `story-C6b`, à jour sur main).

- high — reviewer — corrigé : le script PowerShell du README produisait un fichier que le lecteur
  ignore entièrement (exécuté sur le journal System : 0 événement, « objet invalide » ×N) :
  `MachineName` absent (requis), `Data` sérialisé en tableau d'`XmlElement` au lieu d'un objet,
  `LogName` absent, et un seul événement donnait un objet au lieu d'un tableau. Script réécrit
  (`Data` = objet `Name → #text`, champs de tête, `ConvertTo-Json -InputObject @(...)`) et
  vérifié : 20 événements et 1 événement relus sans ligne ignorée.
- medium — second avis 1 — corrigé : `--modele` inconnu en `local-gere` sur un dossier sans
  détection donnait 0 (moteur jamais ouvert) au lieu de 2 (§4, §19). La commande vérifie le
  nom contre le manifeste (`composition.choisir_modele`) avant `executer_incident`, dans
  `cli.py` seulement ; `application/incident.py` (C5) inchangé. Tests : sans détection et démo
  → 2. `fiches` n'en a pas besoin (le moteur y est toujours ouvert).
- low — second avis 2 — consigné, gardé : `_sans_chemin` sur `EntreeInvalide`/
  `ConfigurationInvalide` touche aussi `fiches` (écart à « autres commandes inchangées »,
  limité au message, conforme à AD-8). Test ajouté : `fiches` dossier absent sans chemin absolu.
- low — second avis 3 — corrigé : le message de `PermissionError` affiche la cible
  (`filename2` d'`os.replace`) et non le provisoire `.<nom>.partiel` ; effet aussi sur `fiches`
  (même helper, message seulement). Test : « (verrou) » affiché, « partiel » absent.
- low — second avis 4 — corrigé : la synthèse d'`incident` affiche `rapport-incident.docx (lot
  <id>)` et plus le chemin absolu. Divergence consignée : `fiches` affiche toujours le chemin
  complet (§19 « le chemin du rapport », non modifié).
- low — second avis 5 — corrigé : « Limites connues » reformulées d'après le code : le point
  final est traité par les garde-fous du récit (C4), la limite réelle est l'extraction
  d'indicateurs (IPv4 suivie d'un point final dans un message non relevée, vérifié) ; l'IPv6 de
  prose est retirée du récit, pas des indicateurs (vérifié) ; coupe-circuit et lecture non en
  flux confirmés (AD-6, `read_bytes`).
- low — reviewer — corrigé : `test_incident_modele_externe_surcharge` ne vérifiait pas le
  modèle (`lot_demarre` incident n'a pas de `modele`) ; il contrôle désormais le champ `model`
  des requêtes reçues par le faux moteur.
- Complexité : 0 constat (abonné console en O(1) par événement, aucune structure qui grossit).
- Reports : aucun.

## Preuves

- Tests ciblés : `uv run pytest -q --tb=short tests/e2e/test_cli_incident.py
  tests/e2e/test_hors_ligne.py tests/e2e/test_cli.py tests/e2e/test_incident.py` → 49 passés.
- Suite complète : `uv run pytest -q --tb=line -p no:warnings` → 638 passés, 2 désélectionnés
  (`slow`).
- `uv run ruff check` et `uv run ruff format --check` → sans erreur.
- Contrôle rapide (`controle_rapide.py`) → sortie nette, code 0.
