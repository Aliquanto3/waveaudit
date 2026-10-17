# Revue — story C6a (Rapport d'incident Word)

Branche revue : `story-C6a-revue` (depuis `story-C6a` 06f8789, rebase sur `main` b51f412 sans
conflit). Écarts acceptés : `max_preuves` au constructeur (C5 le passe depuis
`config.incident.max_preuves`) ; mention « ligne = rang d'objet » en paragraphe après le
tableau de l'annexe.

## Revue

Détail des constats : section « Revue » de
`_bmad-output/specs/spec-waveaudit-cert/stories/story-C6a-rapport-incident-docx.md`.

- low — second avis — rejeté : « Aucun fait détecté » sur liste vide avec récits (le contrat
  ne fixe que le cas sans détection, couvert).
- low — second avis — corrigé : `max_preuves < 1` → `ConfigurationInvalide`.
- low — second avis — corrigé : test du bandeau première page et pages paires.
- low — second avis — corrigé (spec) : PermissionError non interceptée, comme `ExportDocx`,
  convertie en code 4 par la CLI ; à vérifier dans la commande `incident` (C5).
- low — reviewer — corrigé : test de normalisation/troncature des preuves et absence de reste.
- Complexité : 0 constat.

## Vérifications

Sonde python-docx (modèle avec première page distincte et pages paires, message de 400
caractères avec blancs multiples, hôte avec caractère interdit en XML, fichier `a.JSON`) :
comportement conforme. 426 tests verts ; ruff check et format verts.

## Verdict

Prête à intégrer. Report : test `-o` verrouillé → code 4 dans la commande `incident` (C5).
