---
id: Q5
title: Rebanc EliteBook, consigne révisée et rôles des modèles
status: review
sources:
  - ../stories.yaml
  - ../mesures-qualite.md
  - ../../../implementation-artifacts/bilan-modeles.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/impacts-v2.md
---

# Story Q5 — Rebanc EliteBook, consigne révisée et rôles des modèles

## Livré

- `workflows/fiches/prompt.py` : `CONSIGNES["fr"]` et `CONSIGNES["en"]` révisées ensemble
  (contrats §8 v2, §23). Point de départ : la consigne de l'essai 3 de `bilan-modeles.md`
  (constat type présenté comme un modèle générique, une puce par rubrique, « ne présente pas
  comme constaté… »), plus : titre nouveau pour le cas sans reprendre celui du constat type,
  impact en une ou deux phrases sans recopier l'impact générique, recommandation en deux ou
  trois phrases. Les trois règles du §8 (aucune invention, vecteur CVSS par défaut, JSON
  conforme) sont gardées. `CONSIGNE = CONSIGNES["fr"]` inchangé.
- `config/artefacts.toml` (exception d'AD-18 : `role`, `repeat_penalty`, `duree_indicative_s`) :
  - CAP-7 appliqué mécaniquement : `qwen3-1.7b-q4km` devient `modele_defaut` (médianes sur 3
    seeds : 6/6 ok, recopie 0,45, 36,2 s par fiche), `granite-4.0-1b-q4km` devient `candidat` ;
  - `repeat_penalty = 1.1` pour ces deux modèles, les seuls rebancés ;
  - `duree_indicative_s` : 36,2 (qwen3-1.7b) et 27,9 (granite) ;
  - blocs de ces deux entrées échangés pour garder l'ordre de §11 (moteur, défaut, repli,
    candidats) ; aucun autre champ touché.
- `bilan-modeles.md`, section « v2 — Rebanc EliteBook… (Q5) » : vérification de
  `repeat_penalty` sur b11714, essais A et B, 3 seeds par modèle, agrégats (min et médiane de
  ok, médiane et max de la recopie, médiane des durées), relecture à la main, décision.

## Tests réalignés

- `u/test_config.py::test_manifeste_artefacts` : ordre et rôles (qwen3-1.7b défaut, granite
  candidat), `repeat_penalty` exact par modèle (au lieu de « aucun »), durées indicatives.
- `u/test_composition.py::test_choix_par_ram` : vérifie aussi le nom choisi (qwen3.5-0.8b en
  repli, qwen3-1.7b par défaut) ; `::test_choix_explicite_et_erreurs` : modèles échangés ;
  `::test_repeat_penalty_du_manifeste_prime_sur_la_configuration` : modèle sans réglage =
  qwen3.5-0.8b, plus la valeur 1,1 du vrai manifeste qui prime sur `[moteur]`.
- `u/test_composition.py::test_local_gere_demarre_llama_server` : vert sans modification (RAM de
  2 Gio, donc repli). `u/test_pipeline.py` et `u/test_prompt.py` citent `prompt.CONSIGNE(S)`,
  pas le texte : verts sans modification.

## Tests nouveaux

- `u/test_prompt.py::test_consigne_revisee_cap6_fr_et_en_paralleles` : mêmes puces dans le même
  ordre en fr et en, consignes contre la recopie (titre, description, impact), règles du §8.
- `e2e/test_reel.py` (`slow`) :
  - `test_lot_reel_deux_notes_repeat_penalty_du_manifeste` : lot réel des notes 01 et 11 en fr,
    le vrai moteur reçoit le `repeat_penalty` du manifeste, fiches `ok` sans `langue` ni
    `repetition` ;
  - `test_banc_reel_deux_notes_plafond_recopie` (revue V1) : banc réel sur 01 et 11, modèle par
    défaut, recopie ≤ `PLAFOND_RECOPIE = 0.8`.
  Les 3 tests `slow` du fichier passent sur l'EliteBook (250 s).

## Écarts et reports

- CAP-6 n'est pas tenu à la lettre pour qwen3-1.7b à la seed 242 : 5/6, un `repli_moteur` par
  délai dépassé (180 s) sur un poste chargé, rejoué 6/6. Consigné tel quel dans le bilan.
- Repli qwen3.5-0.8b et candidat MiniCPM5 non rebancés : pas de `repeat_penalty`, durées
  indicatives du prompt livré (désormais sous-estimées avec la consigne révisée).
- Point d'arrêt de la story : Anaël valide (ou infirme) le choix du modèle par défaut sur les
  chiffres du bilan avant fusion. README et docs à réaligner par DOC (défaut qwen3-1.7b).
- `ram_min_defaut_go = 4.5` non remesuré avec qwen3-1.7b en défaut.

## Revue

- medium, second avis 1 : CAP-6 non tenu pour qwen3-1.7b (seed 242, 5/6) non dit dans la Décision — corrigé dans le bilan (CAP-6 par modèle explicite, rejeu hors protocole non compté) ; promotion conforme à CAP-7, gardée ; point à arbitrer par Anaël.
- low, second avis 2 : diagnostic de charge présenté comme hypothèse — corrigé.
- low, second avis 3, 4, 5 : README (DOC), `ram_min_defaut_go`, repli et MiniCPM5 non rebancés — reportés.
- Détail : `implementation-artifacts/revues/story-Q5.md`.

## Arbitrage d'Anaël (2026-10-18)

Infirmé : la règle mécanique de CAP-7 désignait qwen3-1.7b par défaut, mais CAP-6 n'est pas tenu
pour lui sur le protocole (5/6 à la seed 242, délai dépassé). **granite-4.0-1b-q4km reste
`modele_defaut`** (CAP-6 tenu) ; **qwen3-1.7b-q4km reste `candidat`**, choisissable à l'accueil.
`config/artefacts.toml` rééchangé (`role` seul ; `repeat_penalty = 1.1` et `duree_indicative_s`
mesurés au rebanc inchangés sur les deux modèles) ; tests réalignés
(`test_config.py::test_manifeste_artefacts`, `test_composition.py::test_choix_par_ram`,
`::test_choix_explicite_et_erreurs`). Détail : `bilan-modeles.md`, section Décision v2.
