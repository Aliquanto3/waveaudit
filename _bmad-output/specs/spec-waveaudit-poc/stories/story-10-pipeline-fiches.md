---
id: story-10
title: Pipeline fiches et prompt
status: done
sources:
  - ../stories.yaml
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
---

# Story 10 — Pipeline fiches et prompt

## Livré

- `src/waveaudit/workflows/fiches/prompt.py` (contrats §8, AD-4) :
  - `construire(note, constat, prefixe_systeme, taille_max_note) -> list[Message]` : `[system]` =
    préfixe (s'il n'est pas vide, puis saut de ligne) + `CONSIGNE` en français ; `[user]` =
    `<constat>` + JSON des 6 champs (`id`, `titre`, `description`, `impact`, `recommandation`,
    `cvss_vecteur`) + `</constat>`, puis `<note>` + `Actif : …` éventuel + corps tronqué + `</note>`.
    Ni références ni `constat_attendu`.
  - `tronquer(corps, taille_max_note) -> (texte, tronque)` : coupe à `taille_max_note` caractères et
    ajoute `[…tronqué]` ; le pipeline s'en sert pour poser le motif `note_tronquee`.
- `src/waveaudit/workflows/fiches/pipeline.py` (contrats §5, AD-6, AD-15) : `WorkflowFiches` et
  `creer(config, ports)`, déjà référencée paresseusement par `REGISTRE["fiches"]` (registre inchangé).
  - Le catalogue est lu une fois à la création ; `traiter` n'appelle que le moteur.
  - `NoteInvalide` → `non_traitee` (`note_invalide`, la raison en détail) ; score BM25 maximal
    `<= 0` → `non_rattachee` (`aucun_constat`, 3 candidats), sans appel au modèle.
  - Rubrique absente ou non textuelle → `SortieInvalide`. `SortieInvalide` → un seul nouvel essai,
    puis repli `repli_sortie_invalide` ; `MoteurInjoignable` → repli immédiat `repli_moteur`. Le
    repli (texte et métriques du constat type) passe par `garde_fous.appliquer`, avec
    `note_tronquee` éventuel en tête des `motifs_initiaux`.
  - `assembler` sépare `Fiche` et `EntreeEcartee` en conservant l'ordre reçu (le tri par nom
    reste au lot, AD-8).
- `tests/unitaires/test_pipeline.py` : vrai `MoteurOpenAI` sur `faux_moteur`, catalogue, notes et
  exporteur en mémoire ; tous les cas de `invoke_dev_with` plus rubrique absente, troncature
  conservée dans le repli, préfixe système transmis, `preparer`/`assembler`.

## Écarts au contrat

- Aucun. `tronquer` est un ajout public de `prompt.py` pour que le pipeline sache s'il y a eu
  troncature sans changer la signature de `construire`.

## Reports

- La note `01-xss-reflechi.md` est rattachée à `WEB-XSS-STOCKE` et non `WEB-XSS-REFLECHI` : le
  test nominal ne vérifie pas l'identifiant retenu ; calibrage en story 11 (CAP-3).

## Revue

| Sévérité | Source | Constat | Décision | Motif |
|---|---|---|---|---|
| low | second avis 1 | `corps` et `actif` insérés tels quels : un `</note>` dans la note ferme la délimitation (injection de consignes) | rejeté, écart à arbitrer | reproduit par construction, mais §8 fige la forme exacte du message `user` ; vraisemblance faible (l'auditeur écrit ses notes ; les notes de démo contiennent des charges HTML, pas `</note>`) ; en aval, les garde-fous imposent références et CVSS du constat type et la fiche est relue. Échapper les balises serait un écart au §8 : à décider au contrat |
| medium | second avis 2 | Le nouvel essai rejoue les mêmes messages avec seed fixe (42) et température 0.2 : sur llama-server, sortie très probablement identique, donc essai sans effet | reporté | §5 dit « un seul nouvel essai » sans plus ; varier la seed demanderait de changer le port `Moteur.generer_json` (socle, AD-0). Vérification sur le vrai SLM (banc) : compter les seconds essais qui réussissent ; si aucun, amender §5 (seed + 1 ou message correctif) |
| low | second avis 3 | Moteur tombé en cours de lot : repli note par note, jusqu'à `timeout_s` (180 s) par note | reporté | conforme au §5 (repli immédiat par note) ; coupure du lot au-delà de N `repli_moteur` consécutifs : à arbitrer avec la story 12 (lot) |
| info | second avis 4 | Seul le premier candidat est transmis au prompt | rejeté | conforme au §5 et §8 |
| low | dev | `01-xss-reflechi` rattachée à `WEB-XSS-STOCKE` | reporté | calibrage CAP-3, story 11 |
| info | revue | `prompt.tronquer` public, absent du §8 | accepté | ajout sans effet sur `construire` ; évite de changer sa signature |

Tests : ciblés 15 verts (`test_pipeline.py`) ; suite complète 211 verts.

Revue : 20 notes de démo par le registre (`CatalogueYaml`, `NotesFichiers`, vrai `MoteurOpenAI` sur faux moteur) : nominal 20 fiches ok en 20 requêtes ; `json_invalide` 20 `a_revoir` en 40 ; `erreur_500` 20 `a_revoir` en 20. Complexité : 0 constat. Suite complète 211 verts, ruff vert.
