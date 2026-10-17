# Revue de la story C2 — lecture des journaux et jeu de démonstration

Branche `story-C2-revue`, rebasée sans conflit sur main (C3, C4, C6a intégrées).
Constats, tri et corrections détaillés : section « Revue » de
`_bmad-output/specs/spec-waveaudit-cert/stories/story-C2-lecture-journaux-demo.md`.

## Constats

- medium (3), tous corrigés : `sysmon.csv` en `\r\r\n` et numérotation CSV qui comptait
  chaque `\r` ; oracle sans `system.json:7` dans le compte `administrateur` ; fichier Windows
  non UTF-8 qui levait `UnicodeDecodeError`.
- low (6) : 2 corrigés (Id `²`, UTF-16 sans BOM), 3 rejetés comme conformes au §21 (passage
  d'année, décalage déjà validé par la configuration, racine JSON non tableau), 1 consigné
  (lecture non en flux).
- Complexité : 0 constat.

## Vérifications

L'oracle est confronté au moteur réel (lecture → `detecter` → `extraire`) : 16 détections et
16 indicateurs identiques, part bénigne 0,65, 80 événements. Suite complète : 601 tests verts.
`ruff check` et `ruff format --check` verts.

## Verdict

Prête à intégrer. Aucun écart au contrat. Report : branchement de `SourceJournauxFichiers`
dans la composition, prévu par C5.
