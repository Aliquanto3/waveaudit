---
id: Q3
title: Catalogue bilingue et traduction anglaise des 50 constats
status: review
sources:
  - ../stories.yaml
  - ../SPEC.md
  - ../formats.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/impacts-v2.md
---

# Story Q3 — Catalogue bilingue et traduction anglaise des 50 constats

## Livré

- `adaptateurs/catalogue_yaml.py` (contrats §15 v2, CAP-8) :
  - `_charger` (chargement strict, `CatalogueYaml.constats()`/`obtenir`) refuse désormais
    toute entrée dont `en` est `None` : `ConfigurationInvalide`,
    `"<fichier>:<index>: textes anglais manquants (en.titre, en.description, en.impact,
    en.recommandation)"`. Une entrée dont le bloc `en` est présent mais incomplet (champ
    manquant ou vide) est déjà refusée en amont par `ConstatType.model_validate` (le
    socle v2, `TextesConstat._non_vide`), avec le message générique « constat type
    invalide (…) » : les deux cas sont bien refusés, avec deux formulations différentes
    selon que `en` est totalement absent ou partiellement rempli.
  - `verifier()` ajoute `_verifier_textes_anglais` : une erreur par champ vide ou par bloc
    `en` absent, au format `"<fichier>:<id>: textes anglais manquants (en.<champ>)"`
    (contrats §15). Le contrôle par champ est défensif (pydantic bloque déjà un `en`
    incomplet avant que `verifier` n'atteigne cette fonction) ; il documente la règle du
    contrat indépendamment de cette implémentation.
  - Aucun changement à `IDENTIFIANTS_FIGES`, `TOTAL_MINIMAL`, aux contrôles CVSS/références
    existants, ni à `domaine/modeles.py` (socle S0, non touché).
- `donnees/catalogue/{ad,autre,config,crypto,infra,web}.yaml` : les 50 entrées reçoivent un
  bloc `en` (`titre`, `description`, `impact`, `recommandation`) traduit en anglais
  professionnel d'audit cyber par le développeur de la story, sans outil de traduction en
  ligne. `id`, `famille`, `mots_cles`, `cvss_vecteur`, `references` (`id`, `titre`, `url`) et
  `source` restent inchangés, comme prescrit par `formats.md`. Les 50 `en.titre` diffèrent
  de leur `titre` français (vérifié par script avant le commit) ; `TITRES_IDENTIQUES_ADMIS`
  (test, revue E38) reste donc vide.
- Tests réalignés dans `u/test_catalogue.py` : `CONSTAT_MINIMAL` porte un bloc `en` complet ;
  toutes les fixtures dérivées (`_catalogue_complet`, tous les `test_verifier_detecte_*`,
  tous les `test_charger_leve_*`, `test_constats_leve_configuration_invalide_si_id_duplique`)
  en héritent sans changement de leur assertion propre.
  `test_contenu_du_catalogue_du_depot_suit_le_cahier_des_charges` contrôle en plus, pour
  chaque constat du dépôt : présence de `en`, `en.titre != titre` (sauf
  `TITRES_IDENTIQUES_ADMIS`), les 4 textes anglais non vides, et
  `motif_langue(en.description, "en")  is None` (aucun mot-outil français).
- Tests nouveaux dans `u/test_catalogue.py` : `test_verifier_detecte_en_absent`,
  `test_verifier_detecte_en_incomplet`, `test_charger_leve_configuration_invalide_si_en_absent`,
  `test_charger_leve_configuration_invalide_si_en_incomplet`.
- Nouveau dans `u/test_qualite_texte.py` :
  `test_aucun_faux_positif_sur_les_textes_en_du_catalogue` (mesure du contrat, symétrique du
  test français existant : `motif_langue(texte, "en") is None` et `est_repetitif(texte) is
  False` sur `description`/`impact`/`recommandation` de `en` pour les 50 constats).
- Tests gardés verts sans modification de leur assertion : `e2e/test_cli.py`
  `test_catalogue_verifier_depot_valide_code_0`, `test_catalogue_verifier_casse_code_2`.
- `domaine/recherche.py` (index BM25 bilingue) et `mots_cles` : non touchés (hors
  périmètre Q3, réservés à Q4 selon `stories.yaml`).

## Échantillon soumis à relecture (10 ids, un par fichier au moins)

- `AD-KERBEROASTING` (ad.yaml)
- `AD-ADCS-ESC1` (ad.yaml)
- `AUTRE-MFA-ABSENTE` (autre.yaml)
- `CONFIG-DEBUG-ACTIF` (config.yaml)
- `CONFIG-CORS-DEBUG` (config.yaml)
- `CRYPTO-HACHAGE-FAIBLE` (crypto.yaml)
- `INFRA-IPMI-EXPOSE` (infra.yaml)
- `INFRA-LLMNR-NBTNS` (infra.yaml)
- `WEB-XSS-REFLECHI` (web.yaml)
- `WEB-SSTI` (web.yaml)

## Choix d'interprétation

- Le contrat §15 écrit une seule formulation d'erreur (« textes anglais manquants
  (en.<champ>) ») pour « bloc absent » et « bloc incomplet ». Le socle v2 (S0) a déjà rendu
  `TextesConstat` strict (chaque champ non vide via `field_validator`) : un `en` présent
  mais avec un champ manquant ou vide est donc déjà intercepté par la validation pydantic
  de `ConstatType`, avant que le code propre à Q3 ne s'exécute. Plutôt que de dupliquer
  cette logique, Q3 ajoute une vérification explicite seulement pour le cas « `en`
  totalement absent » (le seul que pydantic laisse passer, puisque `en: TextesConstat |
  None = None`), et documente le cas « incomplet » par un test qui vérifie le refus sans
  imposer un message précis déjà couvert ailleurs.
- `TITRES_IDENTIQUES_ADMIS` est déclaré vide : aucun des 50 titres anglais rédigés ne
  reprend tel quel le titre français (vérifié par script). L'ensemble existe pour rester
  disponible si une future entrée (Q4 ou au-delà) a un titre réellement intraduisible.

## Reports

- Aucun écart constaté sur le périmètre Q3 ; `domaine/recherche.py` et `mots_cles` restent
  pour Q4 comme prévu par `stories.yaml`.

## Revue

- Point d'arrêt : Anaël relit l'échantillon de 10 constats listé ci-dessus avant fusion
  (CAP-8, `stories.yaml`).
