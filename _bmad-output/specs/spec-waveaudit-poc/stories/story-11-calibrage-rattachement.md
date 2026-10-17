---
id: story-11
title: Calibrage du rattachement (CAP-3)
status: review
sources:
  - ../stories.yaml
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
---

# Story 11 — Calibrage du rattachement (CAP-3)

## Livré

- `tests/unitaires/test_rattachement_demo.py` : charge le vrai catalogue (`donnees/catalogue`)
  et les 20 vraies notes de démonstration (`donnees/demo/notes`), classe chaque note avec le
  vrai BM25 (`domaine.recherche.classer`, réglages par défaut `ConfigRecherche`) et vérifie les
  seuils de CAP-3 (au moins 18 notes dans le top 3, au moins 15 en premier), sans modèle. En cas
  d'échec, le message affiche la matrice des notes hors top 3 (et tous les rangs pour le seuil
  top 1).
- Mesure avant calibrage : 15/20 en premier, 18/20 dans le top 3 (`03-injection-sql` et
  `05-idor` hors top 3 ; `01-xss-reflechi` dans le top 3 mais classé 2ᵉ derrière
  `WEB-XSS-STOCKE`).
- `donnees/catalogue/web.yaml` : `mots_cles` enrichis pour trois constats, chacun avec des
  tournures qui reprennent le vocabulaire effectivement employé dans la note correspondante
  (identique à un rapprochement qu'un humain ferait), sans jamais ajouter l'identifiant ni le
  titre du constat :
  - `WEB-INJECTION-SQL` : contournement par concatenation sans paramétrage, temporisation
    (`sleep`), connexion en admin sans mot de passe valide — vocabulaire de `03-injection-sql.md`
    qui ne contient ni « injection » ni « sql ».
  - `WEB-IDOR` : numéro de facture consécutif dans l'URL, absence de vérification
    d'appartenance, accès à la même ressource via une autre session — vocabulaire de
    `05-idor.md`, qui ne contient ni « idor » ni « autorisation ».
  - `WEB-XSS-REFLECHI` : paramètre renvoyé sans échappement, script exécuté côté navigateur,
    lien piégé pour détourner la session — pour départager `01-xss-reflechi.md` de
    `WEB-XSS-STOCKE`, qui le devançait via un recoupement fortuit sur « champ de formulaire ».
- Mesure après calibrage : 18/20 en premier, 20/20 dans le top 3 (aucune note hors top 3 ;
  `07-traversee-chemin` et `20-journalisation-insuffisante` restent 2ᵉ, toujours dans le top 3).

## Écarts au contrat (variantes minimales)

- Aucun : le calibrage ne touche qu'à `mots_cles` du catalogue, sans modifier `recherche.py`
  (algorithme, paramètres, liste des mots vides inchangée) ni le corps des notes de
  démonstration.

## Reports

- Réalisme du corpus (`05-idor`, `03-injection-sql`, etc. sans jargon technique explicite) :
  déjà reporté par la story 5 à la suite du premier banc réel ; non rouvert ici, le calibrage
  est resté dans les limites imposées (mots-clés du catalogue et mots vides de la recherche
  seulement).

## Score consigné

20 notes de démonstration, catalogue réel, réglages BM25 par défaut (`k1=1.5`, `b=0.75`) :
**18/20 en premier, 20/20 dans le top 3** (seuil CAP-3 : 15 et 18).

Tests : ciblé `test_rattachement_demo.py` + `test_catalogue.py` + `test_notes.py` +
`test_recherche.py` (64 verts) ; suite complète 197 verts ; `ruff check` et
`ruff format --check` verts.
