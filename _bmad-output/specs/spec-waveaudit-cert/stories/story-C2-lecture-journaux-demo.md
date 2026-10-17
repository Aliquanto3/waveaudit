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
  (algorithme d'agrégation et table des indicateurs de §21) ; 16 détections, 14 indicateurs
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

(à compléter par le second avis et le reviewer)
