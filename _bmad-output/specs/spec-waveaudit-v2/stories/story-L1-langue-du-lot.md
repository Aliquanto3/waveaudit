---
id: L1
title: Langue du lot de fiches, de la CLI au Word
status: review
sources:
  - ../stories.yaml
  - ../SPEC.md
  - ../formats.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/impacts-v2.md
---

# Story L1 — Langue du lot de fiches, de la CLI au Word

## Livré

- `workflows/fiches/prompt.py` (contrats §8 v2, CAP-8) :
  - `CONSIGNES: dict[Langue, str]` (`"fr"` : consigne v0.1.0 inchangée ; `"en"` : sa
    traduction, qui demande des rubriques rédigées en anglais) ; `CONSIGNE = CONSIGNES["fr"]`
    reste exporté (v0.1.0).
  - `construire(note, constat, prefixe_systeme, taille_max_note, *, langue: Langue = "fr")` :
    la consigne et les textes du constat (`constat.textes(langue)`) suivent `langue` ; clés du
    `<constat>` dans l'ordre `id, titre, description, impact, recommandation, cvss_vecteur`.
    Libellé de l'actif : `Actif : ` (fr) ou `Asset: ` (en).
- `workflows/fiches/pipeline.py` (contrats §5 v2) :
  - `WorkflowFiches` lit `config.fiches.langue` une fois à la construction (`self._langue`).
  - `_rediger` devient `rediger(note, constat_id, candidats) -> Fiche`, public, hors protocole
    `Workflow` : lit le constat par `ports.catalogue.obtenir(constat_id)`, puis les étapes 3 à
    5 du §5 avec `langue=self._langue` (prompt et garde-fous). `traiter` l'appelle avec
    `candidats[0].id`. Ce renommage prépare la régénération d'entrée (§25, hors périmètre L1).
  - `_sortie_de_repli(constat, langue)` construit le repli depuis `constat.textes(langue)`
    (au lieu des champs français `titre`/`description`/…).
- `application/lot.py` (contrats §9, §23) : `executer_lot` calcule
  `langue = requete.langue or config.fiches.langue`, construit `config_workflow` (copie de
  `config` avec `fiches.langue=langue`) et l'utilise pour fabriquer le workflow ;
  `lot_demarre.details` reçoit en plus `workflow` (nom du workflow demandé) et `langue` ;
  l'export de fin de lot passe `OptionsExport(langue=langue)`. `lot.json`/`relecture.json`
  restent hors périmètre (R2).
- `application/banc.py` : `executer_banc` reçoit un paramètre `langue: Langue | None = None`,
  transmis seulement à `RequeteLot(..., langue=langue)` — aucune mesure de recopie ou de
  langue dans `banc.json` (réservé à B1).
- `interfaces/cli.py` : `fiches` et `banc` reçoivent `--langue fr|en` (Typer valide la valeur
  via le type `Langue`, une valeur hors liste donne le code 2 sans toucher au moteur) ;
  défaut `None` → `config.fiches.langue`. Aucun changement aux commandes, options ou codes
  retour v0.1.0 existants ; `incident` ne reçoit pas `--langue` (rapport toujours français).

## Tests réalignés

- `u/test_pipeline.py::test_prefixe_systeme_vient_des_ports`, `::test_prompt_*` : verts sans
  modification (consigne française par défaut, `prompt.CONSIGNE` toujours la consigne fr).
  La fixture `fabriquer` gagne un paramètre `langue: str = "fr"` qui met à jour
  `config.fiches.langue`.
- `u/test_faux_moteur.py::test_nominal_routes_et_requetes` : vert sans modification (construit
  son propre corps de requête, indépendant de `prompt.construire`).
- `e2e/test_lot.py::test_lot_nominal_30_notes` : égalité exacte de `details` étendue à
  `workflow` et `langue`.
- `e2e/test_cli.py::test_fiches_nominal_30_notes_bandeau_et_garde` : vert sans modification.

## Tests nouveaux

- `u/test_prompt.py` : `test_langue_en_consigne_et_constat_anglais_asset` (consigne et textes
  du constat anglais, libellé `Asset:`) et `test_langue_fr_defaut_consigne_francaise`.
- `u/test_pipeline.py` : `test_lot_anglais_textes_anglais` (faux moteur nominal, lot `en` →
  textes anglais) et `test_lot_anglais_repli_textes_anglais` (repli moteur injoignable, lot
  `en` → repli anglais).
- `u/test_pipeline_langue.py` (nouveau, revue A18/CAP-4) :
  `test_fiche_francaise_dans_un_lot_en` (faux moteur `langue_francaise`, lot `en` →
  `a_revoir` et motif `langue`) et `test_fiche_anglaise_dans_un_lot_en_ok` (faux moteur
  `langue_anglaise`, lot `en` → `ok`, aucun motif `langue`).
- `e2e/test_lot.py` : `test_lot_anglais_details_langue_et_word_anglais` (`langue="en"` →
  `details.langue == "en"`, titre du Word = `LIBELLES["en"]["titre"]`) et
  `test_lot_sans_langue_reste_francais` (sans `langue`, lot et Word restent français).
- `e2e/test_cli.py` : `test_fiches_langue_en_rapport_anglais` (`--langue en` → Word aux
  libellés anglais) et `test_fiches_langue_invalide_code_2` (`--langue de` → code 2).

## Choix d'interprétation

- Le contrat §5 v2 ne précise pas le nom exact à donner à la méthode exposée hors protocole ;
  `rediger` reprend le nom donné par le contrat lui-même (« `rediger(note, constat_id,
  candidats) -> Fiche` »).
- `banc.py` ne reçoit que le paramètre `langue` transmis à `RequeteLot` : aucune mesure
  (recopie, comparaison par langue) n'est ajoutée ici, conformément à `invoke_dev_with` qui
  réserve les mesures à B1.
- `lot.json` et la persistance de `relecture.json` (§25, §30) ne sont pas touchés : L1 ne
  fait que calculer et propager `langue` dans `executer_lot` ; leur écriture est la story R2
  (après L1, cf. `stories.yaml`).

## Reports

- Aucun écart constaté sur le périmètre L1. `lot.json`/`relecture.json` (persistance, §25,
  §30) → R2 ; mesures du banc (recopie par langue, §29) → B1 ; CAP-6 (consigne révisée) → Q5 ;
  attribut `lang` du panneau note et du formulaire de fiche dans l'UI (§23 « ce qui ne change
  pas ») → W2 (hors périmètre CLI/Word de L1).

## Revue

- Aucun point d'arrêt dédié : la story n'ajoute pas de contenu métier au catalogue, seulement
  du code et des tests.
