# Revue story W1 — Socle web

Branche `story/W1` (fe38a98, base `main` db81ae3). Revue unique (reviewer, avec la liste du second avis), story à risque sécurité.

Vérifié : ordre du middleware du §26 (Host en minuscules, Origin, `compare_digest`, 411, 413 par route) ; `hotes_test` seulement via `tests/web_outils.py`, la commande `ui` appelle `creer_app(config)` ; CSP, `nosniff`, `no-referrer`, `no-store` sur les refus du middleware, les 404/405/422 et les pages ; échappement Jinja actif (`id_lot` dans `lot.html`) ; aucun script ni style en ligne ; noms de fichiers (composant de chemin, `[. ]$`, réservés Windows, doublons normalisés) ; verrou relâché sur chaque refus ; tous les tests nommés par `invoke_dev_with` et impacts-v2 ligne 26 présents. Sondes exécutées : 500 non prévu, PUT/DELETE/PATCH sans jeton, `Origin: null`.

## Revue

| Sévérité | Source | Constat | Décision |
|---|---|---|---|
| low | second avis 1 | Origin et jeton CSRF limités à POST/PUT : un futur DELETE/PATCH passerait sans jeton (aujourd'hui 405, mais sans contrôle). | Corrigé : Origin et jeton exigés sur toute méthode hors GET/HEAD/OPTIONS ; longueur et taille restent sur POST/PUT (§26). Test `test_put_et_methodes_non_sures_sans_jeton_refuses` (échoue sur fe38a98 pour DELETE). |
| low | second avis 2 | Exception non prévue : 500 en texte brut par `ServerErrorMiddleware`, sans CSP, `nosniff`, `no-store` ni `{detail, code}` (sondé). Cas réel : `OSError` à l'écriture des notes, échec de `fil.start()`. | Corrigé : `call_next` gardé dans le middleware, 500 `erreur_interne` (code hors §26, comme les 4 déjà déclarés), trace dans le journal local. Test `test_erreur_interne_codee_avec_en_tetes` (sans chemin dans le corps). |
| low | second avis 3 | `GET /api/jeton` renvoie le jeton. | Rejeté : prescrit par le §26 [revue E25] ; lisible seulement en même origine (pas de CORS, Host contrôlé contre le rebinding DNS). |
| low | second avis 4 | `no-store` absent sous `/static/`. | Rejeté : écart déclaré, conforme au §26 (JSON et HTML) ; les statiques ne portent pas le jeton. |
| low | second avis 5 | `str(exc)` de `fil.start()` hors `sans_chemin`. | Corrigé : passé par `sans_chemin` (message de `RuntimeError` sans chemin en pratique, alignement avec `_executer_en_fond`). |
| low | second avis 6 | Tests nommés à vérifier ; PUT, `Origin: null`, « aucun GET n'écrit » peut-être absents. | Vérifié : les 7 tests nommés et les 11 à réaligner existent et passent. Ajoutés : PUT (avec DELETE/PATCH), `test_origin_null_refuse`, `test_aucun_get_n_ecrit_sur_le_disque` (règle de l'en-tête de stories.yaml). |
| low | reviewer | 405 converti en `{detail, code}` sans l'en-tête `Allow`. | Laissé : sans effet sur le parcours, aucune route ne le lit. |
| low | reviewer | `POST /lots/` (barre finale) : limite de 256 Kio puis redirection 307 de FastAPI. | Laissé : le JS envoie toujours `/lots` ; refus plus strict, sans risque. |
| — | reviewer | Complexité : 0 constat (`_RegistreLots.lire` ne copie que `evenements[depuis:]`, ajout en O(1)). | — |

## Reports

Aucun : tout est vérifiable sans service réel. Écarts déclarés par la story (codes hors §26, `corps_invalide` multipart, messages `nom_refuse`, 409 sans `occupation` jusqu'à W2, `no-store` hors `/static/`, « trop gros » 400 → 413) : conformes à l'esprit du §26, à entériner à l'intégration ; s'y ajoute `erreur_interne` (500).
