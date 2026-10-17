---
id: story-15
title: Banc de mesure
status: review
sources:
  - ../stories.yaml
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
---

# Story 15 — Banc de mesure

## Livré

- `application/banc.py` (contrats §20, CAP-12) : `executer_banc(dossier, config, modele=None) ->
  Path`, la signature attendue par `interfaces/cli.py` (`module.executer_banc(dossier, cfg,
  modele)`, story 13).
  - Abonné du lot (AD-2) : à `lot_demarre`, lit `pid_moteur` dans `details` et démarre
    `_Echantillonneur`, un fil dédié qui échantillonne `MesureMemoire.rss_octets`
    (`composition.creer_mesure_memoire()`, seul accès du banc à la mesure mémoire) de
    l'application (`os.getpid()`) et, si connu, du moteur, toutes les 0,5 s ; à `lot_termine` ou
    `lot_echoue`, arrête le fil (`Event` + `join`) puis prend un dernier échantillon hors
    concurrence.
  - Durées par note accumulées depuis `fiche_terminee`/`fiche_non_traitee`/`fiche_non_rattachee`.
  - `top1`/`top3`/`etiquetees` recalculés depuis `Tracabilite`/`EntreeEcartee` : comparaison de
    `constat_attendu` aux candidats triés par score décroissant (`domaine.recherche.classer`) ;
    une entrée sans `constat_attendu` n'entre pas dans `etiquetees`.
  - Écrit `var/sorties/<id>/banc.json` au format du contrat (`id_lot`, `modele`, `fiches`,
    `duree_mediane_s`, `duree_max_s`, `pic_rss_app_o`, `pic_rss_moteur_o`, `pic_rss_total_o`,
    `top1`, `top3`, `etiquetees`) et affiche un résumé lisible en console ; renvoie le chemin.
  - Si le lot échoue (erreur hors des replis par fiche, AD-6), l'exception remonte sans écrire
    `banc.json` — traduite en code retour par `_codes_retour("banc")` côté CLI (déjà en place,
    story 13).
- `tests/e2e/test_banc.py` :
  - `_top` testée directement avec des `Fiche`/`EntreeEcartee` construites à la main (candidats
    en tête, en position 2-3, hors top3, non étiquetée) : `top1`/`top3`/`etiquetees` exacts.
  - Lot nominal (`config_test`, notes de démonstration comptées par `glob`, jamais en dur) avec
    une `MesureMemoire` factice à valeur constante : forme complète de `banc.json`, cohérence des
    bornes (`0 <= top1 <= top3 <= etiquetees <= total`, `duree_max_s >= duree_mediane_s >= 0`),
    pic mémoire app égal à la valeur factice, pic moteur à 0 et total égal au pic app (mode
    externe de `config_test` : `pid_moteur` est `None`).
  - Échantillonnage arrêté à `lot_echoue` : `executer_lot` remplacé par un faux qui émet
    `lot_demarre` (avec un `pid_moteur` fictif) puis `lot_echoue` avant de lever, avec une
    `MesureMemoire` factice qui compte ses appels ; au moins un échantillon pris, puis plus aucun
    après l'arrêt (vérifié par une pause courte sans nouvel appel).
- `tests/e2e/test_cli.py` : `test_banc_dossier_absent_code_2` remplace
  `test_banc_module_absent_code_2` (devenu obsolète : le module existe désormais) — branchement
  réel de la commande `banc` sur `application.banc.executer_banc`, dossier absent -> code 2, sans
  configuration dédiée (l'erreur est levée avant tout accès au moteur ; `banc` n'a pas d'option
  `--config` au contrat). `test_banc_erreurs_traduites_en_codes` (module factice injecté dans
  `sys.modules`) reste inchangé et continue de couvrir la traduction des codes retour.

## Écarts au contrat (variantes minimales)

- `pic_rss_total_o` est la somme des pics app et moteur pris séparément (`max(app) +
  max(moteur)`), pas le pic d'une somme point par point : le contrat ne précise pas le calcul, et
  les deux mesures ne sont pas garanties simultanées (deux appels séquentiels au port par tick).
  Cette somme des pics est une borne haute, simple et déterministe pour les tests.
- Si le lot échoue, `banc.json` n'est pas écrit (comme `fiches.json` dans `application/lot.py`
  pour les mêmes erreurs) : seul le code retour renseigne l'échec, pas de fichier partiel.

## Reports

- `MoteurInjoignable` levée mi-lot par une note réelle est rattrapée par
  `workflows/fiches/pipeline.py` (repli AD-6, motif `repli_moteur`) : elle ne déclenche jamais
  `lot_echoue`. Le test d'arrêt de l'échantillonnage à `lot_echoue` passe donc par un
  `executer_lot` remplacé plutôt que par un vrai scénario de faux moteur — à revoir si une story
  ultérieure a besoin d'un vrai scénario `lot_echoue` après `lot_demarre` (par exemple un échec de
  l'export).

## Tests

`uv run pytest -q --tb=short tests/e2e/test_banc.py tests/e2e/test_cli.py` : 24 verts. Suite
complète, `ruff check` et `ruff format --check` : voir rapport final.

## Revue

- medium, second avis : fil d'échantillonnage non arrêté si `lot_echoue`/`lot_termine` n'atteint pas l'abonné — corrigé (`finally`, `arreter` idempotent).
- low, second avis : pas de test de l'arrêt sur exception hors abonné — corrigé (test ajouté).
- low, second avis : `pic_rss_total_o` somme de deux pics non simultanés — corrigé (maximum de la somme par échantillon) ; interprétation à consigner dans contrats §20.
- low, second avis : course après `join(timeout=2.0)` — rejeté (seulement si `rss_octets` bloque plus de 2 s, effet borné à un échantillon).
- low, second avis : pas de test CLI du chemin de succès — corrigé (`test_banc_succes_code_0`).
- Complexité : 0 constat.

Détail : `_bmad-output/implementation-artifacts/revues/story-15.md`.
