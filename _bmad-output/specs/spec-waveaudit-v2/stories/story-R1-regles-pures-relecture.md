---
id: R1
title: Règles pures de relecture
status: review
sources:
  - ../stories.yaml
  - ../SPEC.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/impacts-v2.md
  - story-S0-socle-v2.md
---

# Story R1 — Règles pures de relecture

## Livré

- `domaine/relecture.py` (formes de S0 inchangées) : ajout de cinq fonctions pures, sans
  accès disque (contrats §25 « Règles pures ») :
  - `fiche_courante(e) -> Fiche` : `fiche_generee` sans correction ; avec `fiche_corrigee`,
    copie de `fiche_generee` avec les 4 textes, `references` et `cvss` corrigés — si le
    `cvss` corrigé vaut `None`, le `cvss` généré est gardé (brouillon) ; `statut`, `motifs`
    et `tracabilite` restent ceux de la génération.
  - `corriger(e, correction, longueur_max) -> EntreeRelecture` : refus (dans l'ordre)
    `non_modifiable`, `generation_en_cours`, `rubrique_trop_longue`, `reference_ajoutee`,
    `reference_dupliquee` (revue E29) ; sinon `cvss` recalculé par `cvss31.evaluer` (vecteur
    invalide → `cvss=None`, saisie conservée, revue E30), références rangées dans l'ordre de
    `fiche_generee.references`, `statut_relecture="a_valider"` ; une correction identique à
    l'état courant renvoie l'entrée inchangée (pas d'incrément de version, géré par la
    persistance R2).
  - `valider(e) -> EntreeRelecture` : refus `non_modifiable`, `generation_en_cours`,
    `vecteur_invalide` (CVSS corrigé `None`), `rubrique_vide` (une rubrique de la fiche
    courante vide après `strip`) ; sinon `statut_relecture="validee"`.
  - `remplacer_fiche(e, fiche, constat_id, modele_generation) -> EntreeRelecture` :
    `etat="fiche"`, `fiche_generee`, `fiche_corrigee=None`, `candidat_choisi=constat_id`,
    `ecartee=None`, `statut_relecture="a_valider"`, `generation="aucune"`,
    `erreur_generation=None`, `modele_generation` (revue A16).
  - `rapport_export(etat, mode) -> tuple[Rapport, frozenset[str]]` : `final` = fiches
    validées (ensemble renvoyé = notes des entrées `fiche` encore `a_valider`, revue A17) ;
    `brouillon` = toutes les entrées `fiche` (même ensemble) ; les deux : `ecartees` = entrées
    `ecartee` plus les entrées `attente` converties en `EntreeEcartee(non_traitee,
    Motif(lot_interrompu, "lot interrompu avant cette note"), candidats=[],
    constat_attendu=source.constat_attendu if source else None)` (revue E17), triées par
    `index`.
- `tests/unitaires/test_relecture_regles.py` (nouveau) : un test par règle et par refus,
  CVSS recalculé, vecteur invalide → validation refusée, ajout et doublon de référence
  refusés, ordre des références, correction identique sans incrément, validée puis modifiée
  → `a_valider`, `fiche_courante` garde statut/motifs/tracabilité et le CVSS généré si le
  corrigé vaut `None`, `rapport_export` final et brouillon avec l'ensemble des non validées,
  entrées `attente` → `lot_interrompu` dans les écartées (avec et sans source), ordre des
  écartées par `index`.

Aucun fichier du socle modifié ; `domaine/cvss31.evaluer` est le seul point d'appel CVSS
(story 3), comme demandé par `invoke_dev_with`.

## Choix d'interprétation

- « Pas d'incrément de version » (corriger, cas identique) est implémenté dans la règle pure
  elle-même : `corriger` renvoie l'entrée reçue sans modification quand la correction calculée
  est égale à `fiche_corrigee` courant (ou, sans correction, à la fiche générée), quel que soit
  le statut : une fiche validée le reste (revue R1). La
  persistance (R2, `application/relecture.py`) peut ainsi détecter l'absence de changement
  sans logique supplémentaire : comparer le résultat à l'entrée d'origine suffit.
- Les règles renvoient une copie revalidée (`EntreeRelecture.model_validate`), jamais un
  `model_copy` seul, qui ne vérifie pas les invariants. Le cas A14 (`non_rattachee`, constat
  pris dans tout le catalogue) passe le validateur S0 ; un `constat_id` hors candidats ailleurs
  fait lever `RefusRelecture("candidat_inconnu")` par `remplacer_fiche` (revue R1).
- Ordre des refus de `corriger` : `reference_ajoutee` avant `reference_dupliquee`, repris de
  l'ordre des puces du contrat (E29 est une puce ajoutée en revue, après `reference_ajoutee`).
- `valider` calcule `fiche_courante(e)` avant de vérifier `vecteur_invalide`, pour que
  `rubrique_vide` porte sur les textes effectivement affichés (corrigés ou générés).

## Reports

- La persistance (verrou par fichier, écriture atomique, `conflit_version`,
  `demarrer_regeneration`, normalisation « génération interrompue ») est R2, hors périmètre
  de cette story.
- Le contrôle d'existence d'un `constat_id` hors `candidats` (régénération depuis
  `non_rattachee` ou correction d'un autre constat) reste à la route (R2/W2), comme prévu.

## Revue

Détail : `_bmad-output/implementation-artifacts/revues/story-R1.md`.

- medium | second avis 1 | corrigé | `remplacer_fiche` sans revalidation pouvait produire une entrée illisible ; copie revalidée, `candidat_inconnu`.
- medium | second avis 2 | corrigé | correction identique sur une fiche validée la repassait à `a_valider`.
- medium | second avis 3 | corrigé (test `is`) ; consigne R2 | `modifier` n'incrémente pas une entrée inchangée ; texte du §25 `modifier` à arbitrer.
- low | second avis 4 | corrigé | test du vecteur invalide dans `corriger`.
- low | second avis 5 | rejeté | forme S0, jugée voulue en revue S0.
- low | reviewer | reporté | `evaluer` accepte `CVSS:3.0` et les métriques temporelles ; à arbitrer.
- Complexité : 0 constat.
