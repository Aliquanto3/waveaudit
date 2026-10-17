---
id: story-5
title: Notes brutes et jeu de démonstration
status: review
sources:
  - ../stories.yaml
  - ../formats.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
---

# Story 5 — Notes brutes et jeu de démonstration

## Livré

- `src/waveaudit/adaptateurs/notes_fichiers.py` : `NotesFichiers` implémente le port
  `domaine.ports.SourceNotes` (contrats §3, §14).
  - `lire(dossier)` sélectionne `*.md`/`*.txt` (extension insensible à la casse), sans descendre
    dans les sous-dossiers, triés par `casefold()` du nom ; `EntreeInvalide` si le dossier est
    absent ou ne contient aucune note de ce type (les autres fichiers, p. ex. `.png`, sont
    ignorés sans compter comme note).
  - Lecture en `utf-8-sig` (BOM tolérée) puis normalisation `\r\n` → `\n`. En-tête YAML reconnu
    seulement si la première ligne vaut exactement `---`, refermé par la prochaine ligne `---` ;
    sinon tout le fichier est le corps.
  - `NoteInvalide(fichier, raison)` en une ligne pour : encodage illisible, en-tête non refermé,
    YAML d'en-tête illisible, en-tête qui n'est pas un mapping, et `corps` vide après strip
    (`ValidationError` du modèle `Note`, attrapée ici, jamais propagée).
  - Tolérance : une clé d'en-tête inconnue est ignorée (log `warning`) ; une
    `severite_pressentie` hors liste devient `None` (log `warning`) sans invalider la note.
- `donnees/demo/notes/01-xss-reflechi.md` … `20-journalisation-insuffisante.md` : 20 notes
  fictives de consultant, style télégraphique, vocabulaire différent du catalogue, preuves
  textuelles fictives (`exemple.test`, `*.local`, `192.0.2.0/24`), sans jamais citer
  l'identifiant du constat ni de CWE dans le corps. `constat_attendu` distincts, pris dans la
  liste figée de contrats §16 (10 web, 3 ad, 2 infra, 2 crypto, 2 config, 1 autre), fichier
  nommé `NN-<id en minuscules sans préfixe de famille>.md`.
- `tests/donnees/notes/` : cas invalides (`corps-vide.md`, `yaml-casse.md`,
  `entete-non-mapping.md`, `severite-hors-liste.md`), `ignoree.png` (ignoré) et
  `hors-sujet.md` (21ᵉ note, recette de cuisine, sert de fixture `non_rattachee` pour une story
  ultérieure).
- `tests/unitaires/test_notes.py` : les 20 notes de démonstration (toutes valides, 20
  `constat_attendu` distincts et figés, familles minimales couvertes, aucune citation du
  constat ni de CWE, preuves fictives présentes, nommage conforme) ; sélection et tri (extension
  insensible à la casse, pas de sous-dossiers, tri `casefold`) ; chaque cas invalide listé
  ci-dessus ; tolérance (champ inconnu, sévérité hors liste, absence d'en-tête, BOM + CRLF
  générés en mémoire sous `tmp_path` pour ne pas dépendre de la normalisation de fin de ligne du
  dépôt).

## Écarts au contrat (variantes minimales)

- Le cas « BOM + CRLF valide » de `invoke_dev_with` est généré dans le test (`tmp_path`), pas
  comme fichier `tests/donnees/notes/` versionné : `.gitattributes` force `eol=lf` sur tout le
  dépôt (empreintes SHA-256 stables), donc un fichier CRLF commité serait reconverti en LF au
  checkout et ne testerait plus la tolérance visée.

## Reports

- Aucun.
