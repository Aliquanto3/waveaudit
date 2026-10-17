---
id: story-10
title: Pipeline fiches et prompt
status: review
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

Tests : ciblés 15 verts (`test_pipeline.py`) ; suite complète 211 verts.
