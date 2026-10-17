---
id: story-2
title: Recherche BM25
status: review
sources:
  - ../stories.yaml
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
---

# Story 2 — Recherche BM25

## Livré

- `domaine/recherche.py` : `classer(constats, requete, *, k1, b) -> list[Candidat]` (contrats §7, CAP-3).
  - Tokenisation : minuscules, NFKD sans diacritique, découpage sur `[^a-z0-9]+`, jetons d'au moins 2 caractères, mots vides français et anglais figés dans le module (`_MOTS_VIDES`).
  - Document indexé par constat : `titre` ×3, `" ".join(mots_cles)` ×3, `description` ×1, concaténés.
  - IDF `ln(1 + (N - n + 0.5) / (n + 0.5))`, score BM25 classique sur `k1`/`b` fournis par l'appelant.
  - Tri par score décroissant puis `id` croissant ; tous les constats sont renvoyés.
  - `requete_depuis_note(note) -> str` : `(note.titre or "") + "\n" + note.corps`, sans jamais lire `constat_attendu` ni `actif` (contrats §7).
- `tests/unitaires/test_recherche.py` : mini-catalogues en mémoire couvrant tokenisation (accents, casse, mots vides), pondération par répétition, IDF toujours positif même quand le terme est présent dans tous les documents, égalité départagée par `id`, requête sans jeton connu → scores à 0, catalogue vide, et `requete_depuis_note`.

## Écarts au contrat (variantes minimales)

- Aucun. Le seuil « non rattachée si score maximal `<= 0.0` » et la limite aux 3 premiers candidats restent du ressort du workflow appelant (hors périmètre de cette story) : `classer` renvoie tous les constats triés, comme demandé par le contrat.

## Reports

- Aucun.
