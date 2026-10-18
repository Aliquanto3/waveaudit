---
id: B1
title: Banc v2 (recopie, taux ok, motifs, langue)
status: review
sources:
  - ../stories.yaml
  - ../mesures-qualite.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/impacts-v2.md
---

# Story B1 — Banc v2 (recopie, taux ok, motifs, langue)

## Livré

- `application/banc.py` (contrats §29) :
  - `executer_banc(dossier, config, modele=None, langue=None, seed=None) -> Path` : `seed`
    remplace `config.moteur.seed` par copie de configuration (`config.moteur.model_copy`),
    sans muter `config` ; défaut : la seed de la configuration. La seed effective (passée ou
    de la configuration) est écrite dans `banc.json["seed"]` et atteint le moteur via la copie,
    comme `requete.modele`/`requete.langue` le font déjà pour `RequeteLot`.
  - `_recopie(fiches, catalogue, langue)` (nouveau, privé) : pour chaque `Fiche` qui n'est pas
    un repli (aucun motif `repli_sortie_invalide` ni `repli_moteur`) et chaque rubrique de
    `RUBRIQUES` (titre, description, impact, recommandation), calcule
    `difflib.SequenceMatcher(None, texte_fiche, texte_catalogue).ratio()` avec `autojunk` à sa
    valeur par défaut ; `texte_fiche` est le champ de la `Fiche` tel qu'écrit dans `fiches.json`
    (aucune normalisation) et `texte_catalogue` vient de
    `catalogue.obtenir(fiche.tracabilite.constat_id).textes(langue)`. Renvoie la moyenne
    globale, la moyenne par rubrique et le nombre de replis ; `None` partout sans fiche
    mesurable (revue A29).
  - `executer_banc` lit le catalogue par `composition.creer_catalogue(config_banc)` (nouveau),
    capture `langue` depuis `lot_demarre.details["langue"]` (comme prescrit par la revue L1,
    plutôt que le paramètre `langue` reçu, qui peut être `None`), puis ajoute à `banc.json` :
    `"langue"`, `"ok"`/`"a_revoir"` (comptage par `Fiche.statut`), `"recopie"`,
    `"recopie_par_rubrique"`, `"replis"`, `"seed"` et `"motifs"` (`Counter` des `Motif.code` de
    toutes les `Fiche`, hors entrées écartées). Les champs v0.1.0 (`id_lot`, `modele`,
    `fiches`, `duree_mediane_s`, `duree_max_s`, `pic_rss_*`, `top1`, `top3`, `etiquetees`) sont
    inchangés. Une ligne console de plus : `ok X/N, recopie 0.xx (titre .. description ..
    impact .. recommandation ..)`.
- `application/composition.py` : ajout de `creer_catalogue(config) -> CatalogueYaml`, seul
  nouvel accès du banc au catalogue (pattern de `creer_mesure_memoire`, AD-2).
- `interfaces/cli.py` : commande `banc` reçoit `--seed INT` (défaut `None` → configuration),
  transmis à `executer_banc` ; aucune autre option, commande ou code retour modifié.

## Tests réalignés

- `e2e/test_banc.py::test_banc_json_nominal` : ensemble exact des clés étendu aux nouveaux
  champs (`langue`, `ok`, `a_revoir`, `recopie`, `recopie_par_rubrique`, `replis`, `seed`,
  `motifs`) ; assertions supplémentaires sur `langue == "fr"`, `seed == config_test.moteur.seed`
  et la forme de `recopie_par_rubrique`.
- `e2e/test_cli.py::test_banc_succes_code_0` : vert sans modification (ne vérifie que
  `pic_rss_app_o`, le nombre de fiches et la présence de `"top1"` dans la sortie console).

## Tests nouveaux (`e2e/test_banc.py`)

- `test_recopie_sans_fiche_est_null` : `_recopie([], ...)` renvoie `(None, {4 rubriques: None},
  0)`, sans jamais consulter le catalogue.
- `test_repli_exclu_de_la_recopie_banc_json` : faux moteur `json_invalide` sur une note unique
  → `replis == 1`, `recopie` et chaque rubrique `null`.
- `test_recopie_nominale_proche_de_un` : faux moteur nominal (`"[adapté] " + texte`) sur une
  note unique → `replis == 0`, `recopie` et chaque rubrique `> 0.8`.
- `test_langue_en_comparee_aux_textes_anglais` : lot `--langue en`, faux moteur nominal → le
  ratio de recopie du titre, recalculé depuis `fiches.json`, est plus proche du texte anglais
  du constat que du texte français ; `recopie_par_rubrique["titre"]` égale le ratio anglais
  recalculé.
- `test_recopie_null_sans_fiche_mesurable` : deux notes, faux moteur `json_invalide` → les deux
  fiches sont des replis, `replis == 2`, `recopie` reste `null`.
- `test_seed_consignee_et_recue_par_le_faux_moteur` : `executer_banc(..., seed=142)` →
  `banc.json["seed"] == 142`, chaque requête reçue par le faux moteur porte `"seed": 142`,
  `config_test.moteur.seed` inchangée (copie, pas mutation).
- `test_seed_defaut_est_celle_de_la_configuration` : sans `seed`, `banc.json["seed"] ==
  config_test.moteur.seed`.

## Choix d'interprétation

- `langue` écrite dans `banc.json` vient de `lot_demarre.details["langue"]` (toujours `"fr"` ou
  `"en"`, jamais `None` : contrats §9 v2, confirmé par la revue L1), plutôt que du paramètre
  `langue` de `executer_banc` qui peut être `None` (défaut configuration) — évite de dupliquer
  la résolution `requete.langue or config.fiches.langue` déjà faite par `executer_lot`.
- « `recopie` : moyenne non pondérée des valeurs ci-dessous » (contrats §29) est lu comme la
  moyenne de toutes les valeurs rubrique × fiche mesurable prises ensemble (et non la moyenne
  des quatre moyennes par rubrique) ; les deux coïncident quand chaque fiche mesurable a ses
  quatre rubriques présentes, ce qui est toujours le cas ici (`Fiche` impose les quatre champs).
- `motifs` compte les codes des `Fiche.motifs` uniquement (fiches `ok` ou `a_revoir`), pas le
  motif unique des entrées écartées (`EntreeEcartee.motif`) : le contrat §29 dit « sur toutes
  les fiches », et les entrées écartées ne sont pas des `Fiche`.
- `creer_catalogue` est ajouté à `composition.py` en fin de bloc des fonctions `creer_*`
  (collision nommée par `stories.yaml` avec Q1/W2/X2/W4, qui ajoutent chacune leur propre
  fonction).

## Reports

- Aucun écart constaté sur le périmètre B1. Le rebanc réel (CAP-6, CAP-7, consigne révisée,
  choix du modèle par défaut) reste Q5 ; aucun test ni mesure sur le vrai modèle n'a été ajouté
  ici.

## Revue

- Aucun point d'arrêt dédié (pas de contenu métier ajouté, seulement le banc et ses tests).
- Revue reviewer (détail : `implementation-artifacts/revues/story-B1.md`) :
  - low, second avis 1 : rubrique complétée comptée dans la recopie — rejeté (conforme à §29, biais prudent), écart à arbitrer avant Q5.
  - low, second avis 2 : `creer_catalogue` en fin de `composition.py` — corrigé.
  - low, second avis 3 : `--seed` borné à 0..2**32-1 (code 2 sinon) — corrigé.
  - low, second avis 4 : oracles exacts (recopie, ok, a_revoir, motifs) et test CLI `--seed` — corrigé.
  - low, reviewer : console `ok X/N` avec N = notes du lot (écartées comprises) — corrigé.
  - Complexité : 0 constat.
