---
id: C2
title: Lecture des journaux Windows et Linux et jeu de démonstration
status: review
sources:
  - ../stories.yaml
  - ../SPEC.md
  - ../formats-incident.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
---

# Story C2 — Lecture des journaux et jeu de démonstration

## Livré

- `src/waveaudit/adaptateurs/journaux_windows.py` : `lire_json` et `lire_csv` (texte déjà
  décodé) selon contrats §21 « Lecture » et formats-incident.md « Champs normalisés ».
  Normalisation des valeurs (`int`→`str`, `bool`→`"true"/"false"`, `dict`/`list`→
  `json.dumps(ensure_ascii=False, sort_keys=True)`, `None`/vide → clé absente). CSV :
  détection du séparateur (`;` si plus fréquent que `,` dans l'en-tête), `ligne` = ligne
  physique de départ de l'enregistrement (gère les champs multilignes quottés).
- `src/waveaudit/adaptateurs/journaux_linux.py` : `lire` (RFC 3164 et rsyslog ISO 8601),
  motifs `sshd`/`sudo`/`useradd` de formats-incident.md, année qui s'incrémente sur un mois
  inférieur au précédent, jamais de décrément, 29 février impossible → `LigneIgnoree`.
- `src/waveaudit/adaptateurs/journaux.py` : `SourceJournauxFichiers` (implémente
  `domaine.ports.SourceJournaux`), routage par nom/suffixe (casse ignorée), encodage
  (BOM UTF-16, sinon `utf-8-sig` Windows / `utf-8` `errors="replace"` Linux), tri final
  `(horodatage, fichier.casefold(), ligne)`.
- `donnees/demo/incident/` (`security.json`, `system.json`, `sysmon.csv`, `auth.log`,
  `syslog`) : 80 événements lus (31 + 7 + 13 + 21 + 8), dont les 29 événements de la
  chronologie d'attaque normative (forme brute reprise des entrées `chrono-*` de
  `tests/donnees/incident/canoniques.yaml`), entourés de bénin repris des entrées
  `benin-*` et de variantes supplémentaires respectant la liste « Bénin autorisé » ; part
  bénigne 0,65 (52/80). Deux lignes volontairement illisibles : `auth.log:6`
  (entrée corrompue) et `security.json:3` (objet sans fuseau).
- `donnees/demo/incident-attendu.yaml` (hors du dossier lu) : oracle au schéma figé de
  formats-incident.md, calculé à la main depuis la chronologie et les fichiers de démo
  (algorithme d'agrégation et table des indicateurs de §21) ; 16 détections, 16 indicateurs
  distincts (6 `compte`, 3 `executable`, 2 `hachage`, 3 `hote`, 2 `ip`).
- Tests : `tests/unitaires/test_journaux.py` (34 cas paramétrés sur `canoniques.yaml` +
  dossier absent/sans fichier routé, fichiers ignorés en silence, BOM UTF-16/UTF-8,
  séparateur `;`, CSV multiligne, JSON racine non tableau, lignes illisibles comptées,
  jour sur un chiffre avec espace, `sudo` sans `[pid]`, ligne ISO rsyslog, passage d'année,
  29 février, routage en casse mixte, `.gz`/`.yaml` ignorés, tri final) ;
  `tests/unitaires/test_demo_incident.py` (lecture de la démo = exactement les `ignorees`
  de l'oracle, au moins 80 événements lus ; absence des valeurs réservées au faux moteur
  dans l'oracle).

## Écarts au contrat

Aucun.

## Reports

- Détections et indicateurs de l'oracle (`donnees/demo/incident-attendu.yaml`) calculés à
  la main par C2 mais seulement partiellement vérifiés ici (C2 n'importe ni
  `domaine.detection` ni `domaine.indicateurs`, comme demandé) : C5 doit les recalibrer
  contre le moteur réel (`detecter`, `extraire`) avant de s'appuyer sur ce fichier, et
  corriger motif à l'appui si l'un contredit formats-incident.md ou §21.

## Revue

- medium, second avis, corrigé : `sysmon.csv` commité en `\r\r\n` (git le voyait binaire), et
  `csv` sur `StringIO(newline="")` compte chaque `\r` : lignes et origines doublées
  (`sysmon.csv:19` au lieu de 10). Fichier remis en LF ; `lire_csv` numérote désormais par
  lignes physiques `\n` (itérateur compteur ; fichier en `\r` seuls découpé sur `\r`),
  `csv.Error` → `LigneIgnoree`. Tests paramétrés CRCRLF/CRLF/LF/CR, test « démo sans `\r` ».
- medium, second avis, corrigé : oracle sans `system.json:7` (104, SubjectUserName
  administrateur) dans les origines du compte `administrateur`. Ajouté à la main d'après
  formats-incident.md (16 indicateurs, et non 14 comme l'annonçait le récapitulatif).
  Nouveau test lecture → `detecter` → `extraire` (code de main) = oracle, part bénigne
  comprise (0,65).
- medium, second avis, corrigé : JSON/CSV non UTF-8 (cp1252) → `UnicodeDecodeError`, contraire
  au §21 (jamais d'exception). Désormais une `LigneIgnoree(ligne=1, "encodage non UTF-8")`.
- low, second avis, corrigé : Id `²` (`isdigit` vrai, `int` lève) → `isascii() and isdecimal()`.
- low, second avis, corrigé : UTF-16 LE sans BOM → une `LigneIgnoree(ligne=1)` au motif
  explicite (octets NUL).
- low, second avis, rejeté : passage d'année sur Jan, Dec, Jan → 2027. C'est la règle exacte
  du §21 (mois inférieur à celui de la ligne acceptée précédente ; jamais de décrément).
- low, second avis, rejeté : décalage `+0200` ; `ConfigIncident.decalage_syslog` valide déjà
  `^[+-]\d{2}:\d{2}$`.
- low, second avis, rejeté : objet JSON unique (ConvertTo-Json d'un seul événement). Le §21
  exige une racine tableau, sinon une `LigneIgnoree(ligne=1)` ; l'accepter serait un écart.
- low, second avis, consigné : lecture non en flux (`read_bytes` du fichier entier),
  acceptable pour le POC.
- Complexité : 0 constat. Lecture, normalisation et extraction linéaires par fichier, tri
  final en O(n log n) ; aucun parcours complet par événement.
- Note : `test_demo_incident` importe désormais `domaine.detection` et `domaine.indicateurs`
  (interdit pendant le développement parallèle, possible maintenant que C3 et C4 sont sur main).
- Branchement : `SourceJournauxFichiers` n'est encore appelée par aucune composition ; c'est
  le rôle de C5.
