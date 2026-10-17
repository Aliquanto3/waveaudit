# Revue story 14 — UI web locale

Branche `story-14-revue` (depuis `story-14`, ecc1cb3, à jour de main sans conflit).

## Constats

| # | Sévérité | Source | Constat | Décision |
|---|---|---|---|---|
| 1 | medium | second avis | `await request.form()` hors `try` après la prise du verrou : un multipart malformé (sans boundary, plus de 1000 fichiers) laisse le verrou pris, puis 409 sur tout `POST` jusqu'au redémarrage (prouvé : 400 puis 409, 409). | Corrigé : tout le chemin avant `Thread.start()` est sous `try/finally` qui relâche le verrou tant que le thread n'est pas lancé. Test `test_multipart_malforme_relache_le_verrou`. |
| 2 | low | second avis | Noms réservés testés sur le stem complet : `CON.x.md`, `NUL .md`, `LPT1.a.md` passaient. Sur ce poste (Windows 11), même `NUL.md` crée un fichier normal ; la faille vaut pour Windows 10. | Corrigé (trivial) : test sur la partie avant le premier point, espaces finaux retirés. Test `test_noms_reserves_windows_avec_point_ou_espace`. |
| 3 | medium | second avis | Avec `ui.hote = "::1"` (permis par §18), le navigateur envoie `Host: [::1]:<port>`, absent de la liste du §18 : 400 sur chaque page (prouvé). | Corrigé : `[::1]:<port>` ajouté aux hôtes (et `http://[::1]:<port>` aux origines). Écart au contrat §18, nécessaire à sa propre clause de démarrage : à consigner dans contrats.md. Test `test_host_ipv6_boucle_locale_accepte`. |
| 4 | low | second avis | Lecture complète de chaque fichier avant le contrôle de 1 Mo. | Corrigé (trivial) : `read(1 Mo + 1)`. Starlette plafonne déjà à 1000 fichiers par formulaire. |
| 5 | low | second avis | `testserver` dans les hôtes de production. | Rejeté : imposé par §18. |
| 6 | low | second avis | `Thread.start()` hors `try` : verrou pris, lot figé `en_cours`. | Corrigé avec le n° 1 (le lot passe `echoue`, le verrou est relâché). |
| 7 | low | second avis | `.docx` absent alors que le lot est `termine` : 500. `id_lot` non filtré, mais borné par le registre. | Corrigé (trivial) : 404 « rapport introuvable ». Le filtrage d'id est rejeté (le registre suffit). |
| 8 | low | second avis | `POST` sans `Origin` accepté. | Rejeté : §18 ne vise que l'`Origin` présent ; un navigateur envoie toujours `Origin` sur un `POST` d'une autre origine. |
| 9 | low | revue (complexité) | Le JS interroge `/etat` chaque seconde, et chaque réponse renvoie et redessine **tout** le journal du lot (copie complète sous verrou côté serveur) : O(n) par interrogation, O(n·durée) sur un lot long (centaines de notes à ~10 s chacune sur CPU). | Corrigé : paramètre facultatif `?depuis=N` (0 par défaut, réponse identique au §18) ; le JS n'ajoute que les nouveaux événements. Test `test_etat_depuis_ne_renvoie_que_les_nouveaux_evenements`. |
| 10 | low | revue | Page `/lots/<id>` d'un lot inconnu : le JS interrogeait sans fin (404 sans `etat`). | Corrigé : arrêt sur 404 avec « Lot inconnu. ». |
| 11 | low | revue | `erreur` du lot exposé tel quel : une exception du moteur peut contenir un chemin absolu (le journal, lui, passe par `_sans_chemin`). | Reporté : affichage local au seul utilisateur, hors contrat. |
| 12 | — | revue | Branchement de la commande `ui` (garde + uvicorn) absent. | Reporté à la story 13 (cli.py), comme l'indique la spec ; `test_architecture` réserve uvicorn à cli.py. À vérifier à l'intégration de la 13 : refus code 2 si `ui.hote` hors `127.0.0.1`/`::1`, `with garde(...)` autour d'`uvicorn.run`. |

Pas de XSS (autoescape Jinja2, `textContent` côté JS), aucune ressource externe.

Complexité : 1 constat (n° 9), corrigé.

## Vérifications

`tests/e2e/test_ui.py` + `test_architecture.py` : 20 verts ; suite complète 250 verts (1 désélectionné `slow`) ; `ruff check` et `ruff format --check` verts.
