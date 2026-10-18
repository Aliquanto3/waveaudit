---
id: Q2
title: Garde-fous v2 (seuils, URL de la note, répétition, langue)
status: review
sources:
  - ../stories.yaml
  - ../SPEC.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/impacts-v2.md
---

# Story Q2 — Garde-fous v2

## Livré

- `domaine/qualite_texte.py` (nouveau, stdlib seule, partagé fiches/incident) :
  - `est_repetitif(texte, source="") -> bool` (contrats §6 étape 5) : trigrammes de mots
    (seuil `len >= 10` et ratio de doublons `>= 0.30`), ou boucle sans espace
    (`(.{3,50}?)\1{4,}`) retenue seulement si elle contient une lettre, fait au moins 40
    caractères et ne figure pas (`casefold`) dans `source`.
  - `motif_langue(texte, langue, source="", *, verifier_mots_outils=True) -> str | None`
    (contrats §6 étape 6) : renvoie le **suffixe** du détail (`"écriture non latine"` ou
    `"mots-outils <autre langue>"`), jamais le nom de rubrique — l'appelant le préfixe en
    `"<rubrique> : <suffixe>"`. Écriture : lettre `Lu`/`Ll`/`Lt`/`Lo` dont le nom Unicode ne
    commence pas par `LATIN`, hors `µ`/`ª`/`º` et catégorie `Lm` ; ignorée si le « mot »
    (jeton sans espace) figure dans `source` (citation). Mots-outils : segments cités
    (`"…"`, `«…»`, `` `…` ``) retirés avant comptage, mot collé à un chiffre jamais compté,
    sigles tout capitales (2+ lettres) ignorés ; signalé si `n_autre >= 2` et
    `n_autre > n_cible`. `MOTS_OUTILS["fr"]` et `["en"]` figées dans le module.
  - `verifier_mots_outils=False` sur le titre : c'est l'appelant qui l'indique, car la
    signature de contrat ne porte pas le nom de rubrique.
- `domaine/garde_fous.py` : ordre révisé d'`appliquer` (contrats §6 v2, CAP-3/CAP-4) —
  `LONGUEUR_MIN_TITRE = 5`, `LONGUEUR_MIN_RUBRIQUE = 20` ; étape 2 (références inventées)
  garde aussi un jeton URL entier et identique (ponctuation finale retirée) à une URL
  extraite de `note.corps` ou `note.actif` (revue A20/E39) ; étapes 5 (répétition) et 6
  (langue), sur les rubriques non complétées à l'étape 4, source = `note.corps` + `actif`.
  Nouveau paramètre `langue: Langue = "fr"` ; le repli (sortie invalide/moteur, géré par
  Q1) passe par `constat.textes(langue)` via ce même paramètre.
- `domaine/garde_fous_incident.py` : même principe pour `appliquer_recit` (contrats §21
  v2, CAP-4) — étapes 5 et 6 sur `titre`/`recit`/`impact`/`recommandation` (écriture) et
  `recit`/`impact`/`recommandation` (mots-outils, jamais le titre) ; `langue: Langue = "fr"`
  (mot-clé). Source = concaténation des `message` des événements de la détection **et**
  des identifiants, IP et hachages déjà reconnus légitimes par les étapes 2 et 3 — un choix
  d'interprétation (voir ci-dessous), nécessaire pour qu'une valeur gardée (ex. un hachage
  répétitif par construction) ne soit jamais lue comme une boucle ou un mot étranger.
- `workflows/*/pipeline.py` non modifiés (Q1 en parallèle) : les deux fonctions reçoivent
  `langue` par mot-clé avec défaut `"fr"`, donc aucun appel existant ne change de
  comportement ; la langue du lot (L1) et du service incident restera `"fr"` tant que ces
  pipelines ne transmettent pas l'argument.
- Tests nouveaux : `u/test_qualite_texte.py` (17 cas : trigrammes, boucle, charges citées
  `../`, `A`, `%2e` à 45 caractères avec et sans citation, écriture non latine, lettres
  modificatrices et ordinaux, citation cyrillique, mots-outils fr/en, `3DES`/sigles,
  citation entre guillemets, titre jamais soumis aux mots-outils, zéro faux positif sur le
  catalogue français) ; `u/test_garde_fous.py` (titre 5/19/4 caractères, autre rubrique 19
  caractères, URL du corps et de l'actif gardées, préfixe d'URL retiré, URL absente
  retirée, répétition, mots-outils anglais dans un lot fr, titre non soumis, écriture
  étrangère, scénario `url_de_la_note` → `ok`) ; `u/test_garde_fous_incident.py` (récit
  anglais → motif `langue` sur `recit`/`impact`/`recommandation`, répétition sur `recit`) ;
  `u/test_pipeline_qualite.py` (nouveau fichier, pour ne pas croiser Q1 :
  `repetition`, `langue_anglaise` en lot fr, `ecriture_etrangere`, `url_de_la_note`) ;
  `e2e/test_incident.py::test_langue_anglaise_a_revoir` (16 récits, motif `langue` sur les
  trois rubriques attendues, le récit reste en français par défaut).
- Tests relus, verts sans modification de leur assertion :
  `u/test_garde_fous.py::test_rubrique_courte_remplacee_par_le_texte_du_constat`,
  `::test_rubrique_vide_remplacee_par_le_texte_du_constat`,
  `::test_references_inventees_retirees_casse_ponctuation_url`,
  `u/test_pipeline.py::test_references_inventees_retirees`,
  `u/test_garde_fous_incident.py` (26 tests après ajout), `e2e/test_lot.py` et
  `e2e/test_incident.py` (démos toujours `ok`).

## Choix d'interprétation

- `motif_langue` ne prend pas le nom de rubrique en paramètre (la signature de contrat,
  §6, ne le porte pas) : il renvoie le suffixe du détail, et c'est `garde_fous.py` /
  `garde_fous_incident.py` qui compose `"<rubrique> : <suffixe>"`. Le mot-clé
  `verifier_mots_outils` (absent de la prose du contrat mais nécessaire pour exclure le
  titre) est la façon la plus simple de porter cette distinction sans dupliquer la
  fonction.
- `<autre langue>` dans le détail `mots-outils` est le code (`"fr"`/`"en"`), pas un nom
  complet (« anglais »/« français ») : le contrat ne fixe pas la forme exacte
  (`"<rubrique> : mots-outils <autre langue>"` est un gabarit), et le code est sans
  ambiguïté et déjà utilisé partout ailleurs dans le domaine.
- Comparaison insensible à la casse (`casefold`) entre un motif répété ou un mot non latin
  et la `source` : une valeur légitime (hachage, IP) peut être recopiée dans une casse
  différente de celle de l'indicateur normalisé, et le contrat ne distingue pas ce cas des
  URL de note (déjà comparées à l'identique, casse comprise, mais ce sont des chaînes
  fournies telles quelles par le consultant, pas des valeurs renormalisées par le domaine).
- Côté incident, la `source` des étapes 5 et 6 inclut, en plus des lignes de preuve, les
  identifiants/IP/hachages reconnus légitimes (étapes 2 et 3) : sans cela, un hachage ou
  une IP valide mais à motif régulier (ex. un hachage de test répétitif) serait lu comme
  une boucle, alors que les étapes 2 et 3 viennent justement de le garder comme légitime.
  C'est la même logique que l'URL de note pour les fiches, étendue à ce que le domaine
  connaît déjà comme légitime plutôt qu'au seul texte brut des preuves.

## Reports

- La langue du lot (passage de `config.fiches.langue` dans `executer_lot` et le service
  incident) reste à L1 : `garde_fous.appliquer` et `garde_fous_incident.appliquer_recit`
  acceptent déjà `langue`, mais les deux pipelines ne la transmettent pas encore (hors
  périmètre Q2, cf. `invoke_dev_with`).

## Revue

- medium | second avis | écriture non latine : citation comparée par jeton (ponctuation collée → faux positif) | corrigé : comparaison par lettre (contrat E35/E36).
- low | second avis | boucle de 40-41 caractères non retenue | rejeté : conforme au motif du contrat.
- low | second avis | trigrammes sans source | rejeté : conforme au contrat.
- low | reviewer | `finditer` au lieu de `re.search` | accepté : suit l'intention du contrat.
- low | reviewer | `casefold` et source incident élargie | écarts déclarés, à arbitrer.
- Complexité : 0 constat. Détail : `implementation-artifacts/revues/story-Q2.md`.
