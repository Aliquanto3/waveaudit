# Revue — story V2 (Banc des 4 modèles et réglage du prompt)

Branche revue : `story-V2-revue` (depuis `story-V2`, rebase sur `main` : déjà à jour, `main` était
ancêtre de `story-V2`). Commit dev : `a43cf8a` (documents seulement :
`_bmad-output/implementation-artifacts/bilan-modeles.md` et
`_bmad-output/specs/spec-waveaudit-poc/stories/story-V2-banc-modeles.md`). Aucun fichier de code
modifié par la revue non plus : tous les constats corrigés sont des erreurs de calcul ou de
rédaction dans ces deux documents.

## Constats

- medium — second avis 1 — corrigé : la « recopie » annoncée pour le contrôle qwen3 (consigne de
  l'essai 3, lot `20261018-021834`) était de 0,39 ; recalculée avec la formule du bilan
  (`difflib.SequenceMatcher` par rubrique contre le constat réellement attaché, moyenne non
  pondérée sur 4 rubriques × 6 fiches) elle vaut 0,51 (description 0,28, contre 0,28 annoncé —
  ce sous-score était déjà juste). Script de recalcul dans le scratchpad de revue, rejoué sur les
  8 lots cités en bas de page. Écarts trouvés et corrigés : banc des 4 modèles (minicpm5 0,83→0,85,
  qwen3 0,76→0,78, qwen3.5 0,82→0,83 ; granite 0,93 confirmé) ; essais 1-3 (0,73/0,35 → 0,77/0,45 ;
  0,79/0,56 → 0,81/0,64 ; 0,74/0,43 → 0,74/0,45) ; contrôle qwen3 (0,39 → 0,51). La formule est
  maintenant décrite précisément dans le bilan (texte brut, non normalisé, constat attaché et non
  l'attendu, moyenne non pondérée).
- medium — second avis 2 — corrigé : la recommandation « qwen3-1.7b adapte nettement mieux » ne
  s'appuyait que sur la mesure du contrôle hors itération (consigne de l'essai 3, non livrée, non
  validée : 4/6 ok, 2 `reference_retiree`). Avec le prompt livré, qwen3 a 6/6 ok mais une recopie de
  0,78, plus basse que les 3 autres (0,83-0,93) mais pas « nettement ». Bilan et story reformulés :
  la recommandation distingue ce qui est mesuré à prompt livré (recopie plus faible, taux ok
  identique) de ce qui reste à valider (gain net de la consigne de l'essai 3 — taux ok à revalider
  sur un lot complet, pas seulement ce contrôle ponctuel) avant de recommander qwen3-1.7b comme
  défaut sur l'EliteBook.
- low — second avis 3 — corrigé : la note 29 a WEB-SSTI en 2e position (DIVULGATION-ERREURS 33,3 /
  SSTI 24,8 / XSS-STOCKE 22,5), pas en 3e. Corrigé aux deux endroits du bilan (tableau de relecture
  et point V1) ; la phrase « 2e ou 3e position » devient « 2e position » (notes 01 et 29 sont
  toutes les deux en 2e).
- low — second avis 4 — corrigé : `temperature` et `max_tokens` n'ont jamais été mesurés seuls (seule
  la consigne a varié sur les 3 itérations) ; « baisser `max_tokens` ne supprimerait pas les
  boucles » est maintenant présenté comme une hypothèse non mesurée, avec sa justification
  (troncature → JSON invalide → repli) inchangée.
- low — second avis 5 — corrigé : définition de « ok » ajoutée en tête du bilan (Protocole) :
  validation mécanique des garde-fous §6 (schéma JSON, CVSS, références, longueur minimale des
  rubriques), explicitement distincte d'un jugement de qualité, pour expliquer pourquoi 6/6 ok et
  0 utilisable tel quel coexistent.
- low — second avis 6 — corrigé : « aucune fiche n'invente » précisé en portée (identifiant,
  référence, URL hors catalogue et hors note — garde-fou §6) et complété par les deux exceptions
  réelles que ce garde-fou ne couvre pas : note 26 (`no_root_squash` présenté comme « parfois »
  constaté sans l'avoir été) et note 01 (constat choisi qui prête à la note une portée — persistance,
  attaque à grande échelle — qu'elle n'a pas).
- low — second avis 7 — corrigé : suite non slow et ruff relancées et consignées (bilan non
  concerné, résultats ajoutés aux Vérifications de la story) : `uv run pytest -q --tb=line
  -p no:warnings -m "not slow"` → 648 passed, 2 deselected (90,8 s) ; `uv run ruff check` → All
  checks passed ; `uv run ruff format --check` → 136 files already formatted.
- low — second avis 8 — corrigé : 129 s = 2 min 9 s, pas 2 min 10 s (`protocole`, run le plus
  long du banc des 4 modèles, lot qwen3).
- Complexité : 0 constat (story documentaire seule, aucun code ni structure qui grossit à
  l'exécution n'est touché).

## Vérifications de la revue

- Tous les chiffres de « recopie » du bilan recalculés indépendamment (script Python,
  `difflib.SequenceMatcher`, scratchpad de revue) à partir de `fiches.json` des lots réels
  (`var/sorties/` du dépôt principal, lecture seule, aucun nouveau run) et du catalogue
  (`donnees/catalogue/*.yaml`) : granite base confirmé à l'identique (0,93 / 0,89), ce qui valide
  la méthode avant d'appliquer les corrections ci-dessus aux autres lots.
- `uv run pytest -q --tb=line -p no:warnings -m "not slow"`, `uv run ruff check`,
  `uv run ruff format --check` : verts (voir ci-dessus).
- Aucun fichier de code modifié, aucun nouveau run du vrai moteur : conforme au cahier (documents
  seulement) et à la consigne de cette revue.
