---
id: Q1
title: Nouvelle tentative seed + 1, balises neutralisées, repeat_penalty transmis
status: review
sources:
  - ../stories.yaml
  - ../SPEC.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/impacts-v2.md
---

# Story Q1 — Nouvelle tentative seed + 1, balises neutralisées, repeat_penalty transmis

## Livré

- `adaptateurs/moteur_openai.py` : `generer_json(..., seed: int | None = None)` (le port
  §3) — `seed` explicite transmis au corps de requête, sinon la seed de configuration du
  constructeur. Constructeur `repeat_penalty: float = 0.0` ; la clé `repeat_penalty` n'est
  envoyée dans le corps que si elle est non nulle (§3, §11).
- `application/composition.py` (`_moteur`) : `repeat_penalty` de l'entrée du manifeste
  (`Artefact.repeat_penalty`) prime sur `config.moteur.repeat_penalty` quand il est renseigné,
  même règle que `mode_json` (§11).
- `workflows/fiches/pipeline.py` (`_generer_avec_un_essai`) et
  `workflows/incident/pipeline.py` (`_generer_avec_un_essai`) : premier essai avec
  `config.moteur.seed`, nouvel essai (après `SortieInvalide`) avec
  `(seed + 1) % 2**32` (contrats §5, E40). `MoteurInjoignable` remonte sans nouvel essai,
  inchangé.
- `workflows/fiches/prompt.py` et `workflows/incident/prompt.py` : `echapper(texte) -> str`
  (`‹` U+2039 à la place de `<` devant `note`/`constat` en fiches, `regle`/`preuves` en
  incident ; même longueur). Appliqué à `note.corps` et `note.actif` avant troncature
  (fiches) et à chaque `ligne_preuve` (incident), pas à `regle` (donnée de confiance du
  catalogue, non échappée).

Tests réalignés : `u/test_pipeline.py::test_json_invalide_une_fois_nouvel_essai_reussi` et
`::test_json_invalide_repli_apres_un_seul_nouvel_essai` (assertions de seed 42 puis 43),
`::test_rubrique_absente_vaut_sortie_invalide` (le faux générateur monkeypatché accepte
désormais `seed`) ; `u/test_pipeline_incident.py::test_json_invalide_une_fois_puis_succes` et
`::test_json_invalide_deux_fois_repli` (mêmes assertions de seed).

Tests nouveaux : `u/test_moteur_openai.py` (seed explicite transmis, seed `None` garde la
configuration, `repeat_penalty` absent du corps à 0.0 et présent sinon) ;
`u/test_composition.py::test_repeat_penalty_du_manifeste_prime_sur_la_configuration` ;
`u/test_prompt.py` (nouveau : balises `</note>`/`<constat>` neutralisées dans le corps et
l'actif, une seule fermante de chaque après échappement, longueur et troncature
inchangées) ; `u/test_prompt_incident.py::test_balise_preuves_dans_un_message_neutralisee` ;
`u/test_pipeline.py::test_seed_maximale_repasse_a_zero` (seed `2**32 - 1` puis `0`).

Tests relus, restants verts sans modification :
`u/test_pipeline.py::test_prompt_balises_dans_le_dernier_user_sans_references_ni_attendu`,
`::test_prompt_sans_prefixe_ni_actif`, `u/test_prompt_incident.py::test_ligne_de_preuve`
(aucune balise dans ces textes, `echapper` n'y change rien).

## Choix d'interprétation

- `_BALISE` cible uniquement les balises *ouvrantes* (`<note>`, `</note>`, etc., casse et
  espaces quelconques) : un `<` qui n'introduit pas `note`/`constat` (fiches) ou
  `regle`/`preuves` (incident) reste tel quel, conformément à la regex du contrat §8.
- Le prompt incident échappe chaque ligne de preuve (contenu potentiellement non maîtrisé des
  journaux), mais pas les champs de la règle (donnée de catalogue, pas une entrée externe) :
  lecture la plus directe de « même règle … appliquée à chaque ligne de preuve » (§8).
- `repeat_penalty` suit exactement le même ordre de priorité que `mode_json` dans
  `composition._moteur` (artefact si renseigné, sinon configuration), par symétrie avec le
  contrat §22 déjà en place pour `mode_json`.

## Reports

- Aucun : le périmètre de Q1 (transmission seed/repeat_penalty, échappement) est couvert en
  entier par les fichiers listés. `domaine/garde_fous*.py` n'a pas été touché (Q2). La
  consigne du prompt (texte, langue) n'a pas été modifiée (L1, Q5).

## Revue

En attente (second avis puis reviewer).
