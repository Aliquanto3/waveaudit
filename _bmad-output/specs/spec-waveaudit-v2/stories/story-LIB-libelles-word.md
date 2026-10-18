---
id: LIB
title: Libellés par langue des statuts et motifs dans le Word
status: review
sources:
  - ../SPEC.md
  - ../formats.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
  - story-X1-rendu-docx-bilingue.md
---

# Story LIB — Libellés par langue des statuts et motifs dans le Word

Ajoutée par arbitrage d'Anaël le 2026-10-18, hors `stories.yaml`. Referme l'écart laissé
ouvert par la revue de X1 (`_bmad-output/implementation-artifacts/revues/story-X1.md`) :
« textes `detail` des motifs et codes bruts (`non_traitee`, `vecteur_invalide`) restent en
français dans un Word `en` ».

## Livré

- `adaptateurs/export_docx.py` :
  - `LIBELLES[langue]["statuts_ecartes"]` (nouveau) : libellé des deux statuts possibles d'une
    `EntreeEcartee` (`non_traitee`, `non_rattachee`), fr et en.
  - `LIBELLES[langue]["motifs"]` (nouveau) : libellé des 12 codes de `CodeMotif`
    (`domaine/modeles.py`), fr et en.
  - `_statut_ecartee_affiche(statut, libelles)` : libellé du statut, repli sur le statut brut
    si absent de la table (défensif ; `CodeMotif`/`Statut` sont des énumérations fermées, le
    repli ne peut normalement pas se déclencher).
  - `_motif_affiche(motif, libelles, langue)` : libellé du code, puis le détail seulement
    quand il reste lisible dans `langue` :
    - `_MOTIFS_VALEUR` (`reference_retiree`, `vecteur_invalide`, `rubrique_completee`,
      `repetition`, `indicateur_retire`, `repli_sortie_invalide`, `repli_moteur`) : le
      `detail` réel de ces codes (grep des appels `Motif(code=...)` dans `src/`) est un jeton,
      un vecteur CVSS, un nom de rubrique ou un message d'erreur technique — une valeur, pas
      une phrase française. Affichée dans les deux langues : `"{libellé} : {detail}"`.
    - Les autres codes (`note_tronquee`, `note_invalide`, `aucun_constat`, `langue`) écrivent
      une phrase française fixe ou quasi fixe (ex. `"corps tronqué à {n} caractères"`,
      `"score BM25 maximal nul"`) : `detail` n'est repris qu'en français ; en anglais, seul le
      libellé est affiché (perte assumée de l'information variable qu'il porte, le texte
      autour étant français — conforme à la consigne : « sinon l'omettre »).
    - `lot_interrompu` : son seul `detail` observé (`"lot interrompu"`,
      `"lot interrompu avant cette note"`) répète toujours le libellé sans rien ajouter :
      jamais affiché, dans aucune langue.
  - Appelés depuis `_section_fiche` (corps d'une fiche `a_revoir`, modes `lot`/`brouillon`) et
    `_annexe` (colonnes Statut et Motif des entrées écartées, tous les modes).
- Tests (`u/test_export_docx.py`) : réalignés sur les libellés (`test_annexe_avec_lot_interrompu`
  et les assertions `vecteur_invalide : ...` des tests existants) sans retrait d'assertion.
  Nouveaux : `test_final_ecartees_en_sans_code_brut_ni_francais`,
  `test_final_ecartees_fr_libelles_et_detail`, `test_brouillon_en_fiche_a_revoir_sans_francais`,
  `test_completude_libelles_motifs_et_statuts_ecartes` (un code de `CodeMotif` ou un statut
  d'entrée écartée sans libellé dans une langue fait échouer ce dernier test).

## Choix d'interprétation

- La catégorisation « valeur » / « phrase française » est faite par code (table statique),
  pas par détection de langue sur le contenu réel du `detail` : les 12 codes sont une
  énumération fermée (`domaine/modeles.py`), leur format de `detail` est fixé par leurs
  rares points d'appel (grep exhaustif dans `src/`) — une détection heuristique de français
  aurait été plus fragile (faux négatifs sur des phrases sans mot-outil, ex. `"corps vide"`,
  `"score BM25 maximal nul"`) qu'une table alignée sur l'usage réel.
- Le fixture de test `vecteur_invalide` utilisait un `detail` rédigé en français
  (`"métrique AC inconnue : X"`) qui ne reflète pas l'usage réel (`detail` = vecteur CVSS,
  `garde_fous.py:103`) ; remplacé par un vecteur CVSS réaliste pour que le test général en
  anglais n'affiche plus de mot français au titre d'un artefact de fixture.

## Écarts ou doutes sur le contrat

- Ni `contrats.md` §27 ni `formats.md` (« Libellés Word par langue ») ne couvrent les statuts
  d'entrée écartée ni les codes de motif : la table `LIBELLES[...]["statuts_ecartes"]` et
  `["motifs"]` de cette story étend `LIBELLES` au-delà de la table normative existante, sans
  la contredire. Signalé, non reporté dans `contrats.md` (hors périmètre de cette story).
- La story X1 avait explicitement laissé cet écart ouvert pour arbitrage ; aucun nouveau doute.

## Revue

Table de libellés ajoutée côté adaptateur (`export_docx.py`), socle AD-0 non touché. Suite
unitaire complète verte (866 tests), `ruff check` et `ruff format --check` propres.
