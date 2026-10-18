# Revue — story ARR (arrêt propre de l'UI, llama-server enfant et `fermer(timeout)`)

Commit relu : 67119a6 (base fd04bc3), branche `worktree-agent-a0f4f716903ce3c3d`. W3b en
parallèle (routeurs, `pages.py`, `export_docx.py`, gabarits, `style.css`) : non touchés.
Verdict : le filet (registre d'objets `LlamaServer`, `terminer_tous`, lifespan, `atexit`) est
juste dans son principe et ne touche aucun processus d'autrui. Mais l'ouverture interrompue
levait `AttributeError` au lieu de `MoteurInjoignable`, et aucun test ne passait par le vrai
`_attendre` : corrigé. Le test `slow` est maintenant probant et a été lancé (vert).

| Sévérité | Source | Constat | Décision |
|---|---|---|---|
| moyenne | second avis 1 | `_attendre` relit `self._processus` à chaque tour ; `terminer_tous` le remet à `None` pendant le sondage `/health` → `AttributeError`, pas l'erreur de domaine annoncée par la spec. | Corrigé : copie locale du processus, drapeau `_arrete` posé par `_arreter` et testé à chaque tour ; `_demarrer` lève `MoteurInjoignable("llama-server arrêté pendant son démarrage")` (sans chemin), sans nouvel essai. Reproduit avant correctif (test rouge sur 67119a6). |
| moyenne | second avis 2 | Tests de `fermer(timeout)` et du lifespan : `__enter__` remplacé entier, le vrai `_attendre` jamais exercé avec un processus tué. | Corrigé : `u::test_terminer_tous_pendant_l_attente_de_health_leve_moteur_injoignable` (faux binaire `jamais_pret`, vrai `_attendre`) et `e2e::test_lifespan_arret_pendant_ouverture_vrai_llama_server_sans_orphelin` (chaîne réelle lifespan → `fermer(timeout)` → `terminer_tous`, sans doublure du filet, pid vérifié mort). Les deux échouent sur 67119a6. |
| faible | second avis 3 | Test `slow` : sous Windows, le Job Object tue llama-server à la mort de l'UI, donc le test ne prouve pas le filet. Un lot d'une note finissait en plus avant la borne de 10 s (fin normale, pas le filet). Il était aussi instable (`NoSuchProcess` entre `is_running` et `status`) et ne nettoyait pas `var/sorties`. | Corrigé : lot de dix notes ; exige que llama-server meure pendant que l'UI vit encore ; durée d'arrêt < 15 s ; `_vivant` tolère `NoSuchProcess` ; lot et journal moteur retirés. Lancé : vert en 16,7 s, lot interrompu à la note 2, aucun llama-server restant (psutil). |
| faible | second avis 4 | Fenêtre entre `Popen` et `_registre.add` ; un second essai de `_lancer` pouvait relancer un serveur déjà arrêté par le filet. | Corrigé : `Popen`, inscription et rattachement au Job sous `_arret_verrou` ; `_lancer` refuse si `_arrete`. |
| faible | second avis 5 | Branche timeout de `fermer` : `_pile`/`_ouvert` non remis à zéro ; si l'ouverture a passé `sonder()` juste avant l'arrêt, un serveur mort reste stocké. | Rejeté : seul appelant le lifespan, suivi de la sortie du processus ; le serveur stocké est déjà arrêté et retiré du registre, `pile.close()` reste idempotent. Toucher l'état sans le verrou serait plus risqué que le défaut. |
| faible | second avis 6 | Borne de 10 s non garantie au pire : `_arreter` peut attendre 5 s + 5 s par serveur après `fermer(restant)`. | Reporté : sous Windows `terminate()` est `TerminateProcess`, l'attente rend la main aussitôt ; mesuré < 15 s de bout en bout par le test `slow` (démarrage d'uvicorn compris). À documenter avec `fermer(timeout)` dans `contrats.md` §24. |
| faible | second avis 7 | `test_terminer_tous_filet…` : `_demarrer()` hors `try/finally`, faux serveur laissé en vie en cas d'échec. | Corrigé : `try/finally` avec `_arreter()` idempotent. |
| — | reviewer | Complexité : 0 constat. Le registre est un `set` de quelques serveurs au plus, parcouru seulement à l'arrêt. | — |

Vérifié conforme : aucun fichier du socle AD-0/AD-18 touché ; registre d'objets (pas de pid),
aucun processus d'autrui touché (test existant) ; `adaptateurs.llama_server` importé par
`composition` seule (`test_architecture.py` vert) ; CLI inchangée ; `fermer()` sans `timeout`
inchangé.
Tests : `tests/unitaires` et `tests/e2e`, 1043 réussis ; `slow -k arret` vert ;
`ruff check` et `ruff format --check` propres.
