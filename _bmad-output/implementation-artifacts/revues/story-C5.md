# Revue de la story C5 — workflow incident, service et calibrage

Branche `story-C5-revue`, rebasée sans conflit sur main. Tri détaillé : section « Revue » de
`_bmad-output/specs/spec-waveaudit-cert/stories/story-C5-workflow-incident-service.md`.

## Constats

- high, medium : aucun.
- low (6, second avis) : 1 corrigé (écritures atomiques d'`incident.json` et de la copie),
  2 consignés (noms privés de `lot.py`, `assembler_rapport` à 3 arguments), 3 rejetés comme
  conformes (chemin saisi dans `EntreeInvalide`, rubrique complétée, pas de coupe-circuit).
- Complexité : 0 constat.

## Vérifications

Lecture du §21 « Prompt et pipeline » et « Service » contre le code : ordre des étapes,
moteur ouvert seulement s'il y a une détection, un seul nouvel essai, repli immédiat sur
`MoteurInjoignable`, `incident.json` = `model_dump_json(indent=2)`. Tests ajoutés : id de lot
refusé (`../evasion`, `-tiret`, `a b`, `NUL`), id fourni sans fichier provisoire résiduel,
`lot_echoue` sans chemin absolu. Suite complète verte, `ruff check` et `ruff format --check`
verts.

## Verdict

Prête à intégrer. Écarts au contrat : `assembler_rapport(lecture, recits, regles)` ; imports
privés de `lot.py` (dette de socle). Reports C6b : affichage des erreurs comme `fiches`,
`PermissionError` de `-o` → code 4.
