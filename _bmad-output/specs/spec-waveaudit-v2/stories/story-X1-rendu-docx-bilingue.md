---
id: X1
title: Rendu Word bilingue, modes final et brouillon
status: review
sources:
  - ../stories.yaml
  - ../SPEC.md
  - ../formats.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/impacts-v2.md
---

# Story X1 — Rendu Word bilingue, modes final et brouillon

## Livré

- `adaptateurs/export_docx.py` :
  - `LIBELLES: dict[Langue, dict]` (nouveau, public) : un dictionnaire par langue (`fr`, `en`)
    portant les intitulés de la table du contrat §27 (titre du document, en-têtes de la
    synthèse, intitulés de rubrique, sévérités, `OK`/`À revoir`, en-tête et intitulés de
    l'annexe, marque, « Validée », motif des fiches non validées) ;
  - `BANDEAUX: dict[Langue, str]` (nouveau, public) : bandeau par langue. `BANDEAU` reste la
    constante publique française, inchangée, réutilisée par `export_incident_docx.py` ;
  - `ExportDocx.exporter(rapport, chemin, options=OptionsExport())` reçoit désormais
    `options` (`OptionsExport` de S0) : rend dans la langue, le bandeau et les libellés
    de `options.langue`, et applique le mode (`lot`, `brouillon`, `final`) ;
  - mode `lot` (défaut) : rendu inchangé par rapport à la v0.1.0, y compris en français ;
  - mode `brouillon` : le titre de niveau 2 d'une fiche dont `tracabilite.note` est dans
    `options.non_validees` devient `"{N}. {titre} — {marque}"` ; la section Statut garde le
    statut de génération et ses motifs, dans les deux modes ;
  - mode `final` : jamais de marque dans le titre ; la section Statut et la colonne Statut de
    la synthèse portent toujours « Validée »/« Validated », sans les motifs de génération,
    quel que soit le statut de génération réel de la fiche reçue ;
  - annexe (`_annexe`) : présente si `rapport.ecartees` n'est pas vide, ou si le mode est
    `final` et `options.non_validees` n'est pas vide. Les entrées écartées se rendent comme
    en v0.1.0 (`Note`, statut brut, `code : detail`) ; en mode `final`, une ligne est ajoutée
    par note de `options.non_validees`, triée par `casefold` pour un ordre déterministe :
    `Note` = nom de la note, `Statut` = la marque, `Motif` = le motif des fiches non
    validées (`[revue A17]`) ;
  - `_bandeau_en_tete_pied(document, bandeau=BANDEAU)` : le bandeau devient un paramètre, avec
    `BANDEAU` en défaut pour ne pas changer l'appel depuis `export_incident_docx.py` ;
  - `[revue E19]` écriture atomique : le provisoire devient
    `.<nom>.<uuid4().hex>.partiel`, retiré dans un `finally` ; pas de changement du
    comportement de `os.replace`.
  - Les titres des références (`Reference.titre`) et les mots-clés inline français (« Vecteur
    :», « Score :», « Sévérité :», « Note :», « Constat type :») ne sont pas traduits : ils
    ne figurent pas dans la table `LIBELLES` du contrat §27 ni dans `formats.md`.
- Tests (`u/test_export_docx.py`) : les 8 tests v0.1.0 restent verts sans changer leurs cas
  (mode `lot` français identique). Nouveaux : `test_en_bandeau_intitules_severites_statuts_annexe`,
  `test_brouillon_marque_sur_les_seules_fiches_non_validees`,
  `test_final_aucune_marque_validee_sans_motifs`, `test_final_annexe_non_validees_fr_en`
  (paramétré fr/en), `test_annexe_avec_lot_interrompu`, `test_aucun_partiel_restant`.

Pas de changement dans `application/export.py` ni `interfaces/cli.py` (X2) : aucun de ces
fichiers n'existe ou n'est touché par cette story.

## Choix d'interprétation

- Les mots français inline de `_section_fiche` qui ne figurent pas dans la table `LIBELLES`
  du contrat (`Vecteur :`, `Score :`, `Sévérité :`, `Note :`, `Constat type :`) restent en
  français dans les deux langues, par cohérence avec « titres des références non traduits » :
  seules les chaînes explicitement listées par `formats.md`/contrats §27 sont traduites.
- Le statut brut d'une `EntreeEcartee` (`non_traitee`, `non_rattachee`) dans la colonne
  Statut de l'annexe n'est pas traduit : ni `formats.md` ni contrats §27 ne lui donnent de
  libellé par langue (contrairement à la marque « Non validée » des fiches non validées,
  elle-même listée).
- `test_annexe_avec_lot_interrompu` couvre le rendu générique d'une entrée dont le motif est
  `lot_interrompu` (contrats §25) : aucun traitement spécifique n'est nécessaire côté rendu,
  l'entrée se rend comme toute `EntreeEcartee`.

## Écarts ou doutes sur le contrat

Aucun. `OptionsExport` et la signature `Exporteur.exporter(..., options=OptionsExport())`
existaient déjà (S0) ; seul l'adaptateur restait à aligner, comme annoncé par la consigne de
la story.
