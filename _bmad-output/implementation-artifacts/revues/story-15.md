# Revue story 15 — Banc de mesure

Branche `story-15-revue` (depuis `story-15`, 164bcb2, rebasée sur main après D2 sans conflit).

## Constats

| # | Sévérité | Source | Constat | Décision |
|---|---|---|---|---|
| 1 | medium | second avis | Pas de `try/finally` autour d'`executer_lot` : si l'écriture du journal échoue avant l'appel de l'abonné (`lot.py`, `_Emetteur.emettre`), `lot_echoue`/`lot_termine` n'arrive pas et le fil d'échantillonnage n'est ni arrêté ni joint. | Corrigé : `finally: echantillonneur.arreter()`, `arreter` rendu idempotent (et sans effet si le fil n'a jamais démarré). |
| 2 | low | second avis | Aucun test de l'arrêt sur exception hors abonné. | Corrigé : `test_banc_echantillonnage_arrete_si_lot_echoue_n_atteint_pas_l_abonne` (OSError sans `lot_echoue`, intervalle 0,05 s). |
| 3 | low | second avis | `pic_rss_total_o` = pic app + pic moteur, pris à deux instants : surestime le pic simultané. | Corrigé : maximum de la somme app + moteur par échantillon. Interprétation à consigner dans contrats §20 (le champ n'y est pas défini). Test `test_pic_total_est_le_pic_simultane` (110, pas 150). |
| 4 | low | second avis | `join(timeout=2.0)` puis échantillon final : course si le join expire. | Rejeté : ne survient que si `rss_octets` bloque plus de 2 s ; les `append` sur liste restent sûrs sous le GIL et l'effet se borne à un échantillon de plus. |
| 5 | low | second avis | Pas de test CLI du chemin de succès de `banc`, demandé par la story. | Corrigé : `test_banc_succes_code_0` (faux moteur via `config_test`, `MesureMemoire` factice, code 0, `banc.json` écrit, garde relâché). |

Branchement CLI vérifié : `cli.banc` importe `waveaudit.application.banc` sous `garde()` et traduit les erreurs (`_codes_retour`) ; il était déjà en place, la story n'avait pas à modifier `cli.py`. Pas d'import typer ni interfaces dans `banc.py`. Aucun test ne suppose 20 notes de démo (comptage du dossier).

Complexité : 0 constat (échantillons ajoutés en O(1), maximum calculé une fois en fin de lot ; ~2 échantillons/s, volume négligeable).

## Vérifications

`tests/e2e/test_banc.py` + `test_cli.py` : 27 verts ; suite complète 277 verts (1 désélectionné `slow`) ; `ruff check` et `ruff format --check` verts.
