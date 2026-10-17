---
id: C3
title: Catalogue de règles et moteur de détection
status: review
sources:
  - ../stories.yaml
  - ../SPEC.md
  - ../formats-incident.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
---

# Story C3 — Règles et moteur de détection

## Livré

- `donnees/regles/windows.yaml` (10 règles) et `linux.yaml` (5 règles) : les 15 règles du
  catalogue minimal, conditions et agrégations recopiées telles quelles depuis
  `formats-incident.md` ; titres, descriptions, impacts et recommandations rédigés en
  propre, en français, sans jeton ATT&CK, IPv4, IPv6 ni hachage ; références ATT&CK
  cohérentes avec les URL MITRE.
- `src/waveaudit/adaptateurs/regles_yaml.py` : `CatalogueReglesYaml(dossier)` (implémente
  `CatalogueRegles`) charge chaque `*.yaml` du dossier trié, valide chaque entrée
  (`Regle.model_validate`) puis appelle `verifier_regles` ; toute erreur lève
  `ConfigurationInvalide` listant toutes les erreurs trouvées. `verifier_regles(regles) ->
  list[str]` contrôle : identifiants uniques, les 15 ids minimaux présents, clés de
  `champs`/`champs_regex`/`au_moins_un`/`agregation.par` dans `CHAMPS_<source>`,
  `programme` dans `PROGRAMMES_LINUX`, regex compilables, URL de référence cohérente avec
  l'id ATT&CK, textes (`titre`, `description`, `impact`, `recommandation`) sans jeton
  interdit et de longueur minimale.
- `src/waveaudit/domaine/detection.py` : `correspond(regle, evenement) -> bool` (public,
  applicabilité seule : source puis chaque critère de `Condition`, clé absente = critère
  faux, regex en `re.IGNORECASE`) et `detecter(regles, evenements) -> list[Detection]`
  (une détection par événement sans agrégation ; avec agrégation, fenêtre glissante sur les
  événements porteurs de tous les champs `par`, groupés par leurs valeurs `casefold`,
  algorithme normatif de contrats §21). `indicateurs` reste vide en sortie ; le module
  n'importe pas `domaine.indicateurs`.
- `tests/unitaires/test_regles.py` : catalogue réel (15 règles, `verifier_regles` sans
  erreur), et chaque défaut de `verifier_regles` isolément (doublon, clé hors champs,
  clé d'agrégation hors champs, programme non reconnu, regex non compilable, URL
  incohérente ou invalide, jetons interdits dans chaque rubrique, titre vide, texte trop
  court, catalogue vide — les 15 ids minimaux signalés manquants, YAML invalide ou racine
  non liste).
- `tests/unitaires/test_detection.py` : test paramétré sur les 34 entrées de
  `canoniques.yaml` (`correspond` retrouve exactement l'ensemble `regles` de chaque
  entrée, contre le catalogue réel) ; vecteurs d'agrégation normatifs (seuil 3/fenêtre 60 :
  deux groupes, perte des deux premiers, borne incluse, aucune détection ; seuil 5/fenêtre
  300 : une détection de 8) ; seuil atteint par des copies espacées de 10 s (une
  détection) contre une copie isolée (aucune) ; `au_moins_un` (déclenche sur une seule clé,
  faux si aucune ne correspond) ; clé absente rend un critère faux ; événement sans le
  champ `par` non compté ; déterminisme (deux exécutions identiques) ; tri final
  (`debut`, `regle_id`, fichier `casefold`, ligne) ; `detecter` laisse `indicateurs` vide.

## Écarts au contrat

Aucun.

## Reports

Aucun.

## Revue

- medium, second avis, corrigé : fenêtre glissante O(n²) réécrite en O(n) (`_fenetres`), équivalence prouvée contre le pseudo-code littéral (jeux aléatoires), test 50 000 événements.
- low, second avis, rejeté : pas de dédoublonnage dans `detecter` ; §21 ne le prévoit pas, unicité de `Evenement.cle` assurée par la lecture (C2) ; à arbitrer en C5 si besoin.
- Complexité : 1 constat (corrigé).

Détail : `_bmad-output/implementation-artifacts/revues/story-C3.md`.
