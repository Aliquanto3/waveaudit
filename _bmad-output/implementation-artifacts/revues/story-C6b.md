# Revue de la story C6b — CLI incident, hors ligne, README

Branche `story-C6b-revue`, depuis `story-C6b`, déjà à jour sur main (aucun conflit). Tri
détaillé : section « Revue » de
`_bmad-output/specs/spec-waveaudit-cert/stories/story-C6b-cli-incident-hors-ligne-readme.md`.

## Constats

- high (1, reviewer) : script PowerShell d'export du README inutilisable (0 événement relu) ;
  corrigé et vérifié sur un vrai journal Windows.
- medium (1, second avis) : `--modele` inconnu sans détection → 0 au lieu de 2 ; corrigé dans
  `cli.py`.
- low (5) : 4 corrigés (cible du message `PermissionError`, synthèse sans chemin absolu,
  limites du README exactes, test `--modele` externe), 1 consigné (`_sans_chemin` partagé avec
  `fiches`).
- Complexité : 0 constat.

## Écarts au contrat

- `_codes_retour` (partagé) : `_sans_chemin` sur les erreurs d'entrée et cible `filename2` pour
  `PermissionError` touchent aussi le message de `fiches` (codes inchangés).
- Synthèse : `incident` affiche le nom du rapport et l'id du lot, `fiches` le chemin complet.

## Verdict

Prête à intégrer.
