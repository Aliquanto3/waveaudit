# Revue — story 12 « Composition, lot et cycle de vie de llama-server »

Branche `story-12-revue` (depuis `story-12`, 4a2360a, déjà à jour sur `main` 8ad1a67, sans conflit). Contrat : contrats §9, §10, §12 ; AD-2, AD-6, AD-8, AD-9, AD-11 ; stories.yaml id 12.

Verdict : prête à intégrer. Le tableau des constats est dans la spec de la story (`_bmad-output/specs/spec-waveaudit-poc/stories/story-12-lot-composition-llama.md`, § Revue).

Corrections : `_sans_chemin` (chemins avec espaces, URL préservées), `id_lot` réservé Windows -> `EntreeInvalide`, test du Job Object rendu stable.

À reporter dans le prompt des stories 13 (CLI), 14 (UI) et du banc : `charger_configuration()` puis `with garde(config.reseau.hotes_autorises):` autour de tout le reste (§12, AD-9) ; `executer_lot` ne pose pas la garde.

Écart au contrat consigné : `composition.ouvrir(config, modele, *, id_lot=None)` (argument nommé optionnel, pour le nom du journal de llama-server).

Tests : ciblés 26 verts ; suite complète 238 verts ; ruff check et format verts.
