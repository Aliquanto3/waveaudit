# Revue story Q5 — Rebanc EliteBook, consigne révisée et rôles des modèles

Branche `worktree-agent-a57f6f15afb8ed9e2` (commit 00051e6, base `main` dfc0886). Jugée sur les
données consignées : aucun banc réel ni test `slow` relancé (autres stories sur le poste).

## Revue

| Sévérité | Source | Constat | Décision |
|---|---|---|---|
| medium | second avis 1 | CAP-6 exige `ok` 6/6 sur chaque seed, hors `repetition` et `langue` seulement ; qwen3-1.7b seed 242 = 5/6 (`repli_moteur`). La section Décision du bilan ne disait pas que le modèle promu ne tient pas CAP-6. | Corrigé (documentation) : la promotion est conforme à la lettre de CAP-7 (médianes 6/6, 0,45, 36,2 s sur les runs du protocole ; CAP-7 ne pose pas CAP-6 comme condition), donc décision non changée. Section Décision et tableau des agrégats rendus explicites : CAP-6 tenu pour granite, non tenu pour qwen3-1.7b sur le protocole ; le rejeu de la seed 242 est hors protocole et non compté. Point à arbitrer rédigé pour Anaël. |
| low | second avis 2 | Diagnostic « charge CPU » non démontré (un rejeu à 68 s, charge mesurée au rejeu seulement). | Corrigé : présenté comme hypothèse non démontrée dans le bilan. |
| low | second avis 3 | README.md encore granite par défaut. | Reporté à DOC (déjà noté dans la spec de story). |
| low | second avis 4 | `ram_min_defaut_go = 4.5` non remesuré ; marge de durée mince (seed 142 à 40,1 s). | Confirmé, reporté : pic RSS de qwen3-1.7b 2,86 Gio au plus, sous 4,5 Go ; déjà en réserve du bilan. |
| low | second avis 5 | Repli qwen3.5 et MiniCPM5 sans `repeat_penalty`, durées de l'ancien prompt. | Confirmé, reporté : hors des deux modèles que CAP-6 nomme ; déjà en écart de la spec. |
| — | reviewer | Agrégats recalculés à la main depuis les tableaux par seed (min/médiane ok, médiane/max recopie, médiane des durées) : justes. Seuls `role`, `repeat_penalty`, `duree_indicative_s` changent par bloc (exception AD-18). | — |
| — | reviewer | Intégration : `choisir_modele` lit le rôle au manifeste, aucun nom de modèle en dur dans `src/` ; les tests de `main` (W2 : `test_modeles_installes`, `test_lots`) utilisent des manifestes synthétiques ; `git merge-tree main HEAD` sans conflit. | — |
| — | reviewer | Complexité : 0 constat (consigne et manifeste statiques, pas de structure qui grossit). | — |

## Reports

- Point à arbitrer par Anaël avant fusion : qwen3-1.7b par défaut (CAP-7 tenu) alors qu'il manque
  CAP-6 d'une fiche (délai de 180 s dépassé, seed 242), ou granite maintenu (CAP-6 tenu). Voie
  possible : rebanc de qwen3-1.7b seed 242 poste au repos, consigné comme reprise du protocole.
- README (défaut qwen3-1.7b) : DOC.
