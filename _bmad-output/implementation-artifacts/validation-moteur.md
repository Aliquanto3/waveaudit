# Validation sur le vrai moteur (story V1)

Mesures brutes du 2026-10-18, sur l'EliteBook cible (correction du 2026-10-18 : le plan de nuit supposait à tort un autre poste).
Les mesures ci-dessous sont celles de la revue (après correction), sans téléchargement concurrent ;
elles remplacent celles de la première passe, prises en partie pendant la fin du téléchargement.

## Machine (psutil et Win32_Processor)

- Processeur : 11th Gen Intel Core i5-1145G7 à 2,60 GHz, 4 cœurs physiques, 8 logiques.
- RAM : 15,7 Gio au total, 7,5 Gio disponibles pendant les lots.
- Windows 11 Entreprise. llama-server b11714 en CPU, `threads = 4`, `ctx = 4096`.
- Configuration livrée : `temperature = 0.2`, `seed = 42`, `max_tokens = 700`.

## Installation

- Commande : `uv run waveaudit installer --candidats`, lancée depuis le dépôt principal.
- Durée : 6 min 15 s pour environ 3,4 Go, d'une traite, sans reprise.
- Empreintes SHA-256 : toutes conformes au manifeste (moteur et 4 modèles).
- Archive llama-server : `llama-server.exe` est à la racine du zip. `executable` reste inchangé dans `config/artefacts.toml`.
- Le worktree pointe sur `var/` du dépôt principal par un `waveaudit.local.toml` ignoré par git (`[chemins] var = "<dépôt>/var"`). Les modèles n'ont pas été copiés. Aucun nouveau téléchargement pendant la revue.

## Diagnostic (sonde brute, hors application)

Appel direct de `/chat/completions` avec le prompt et le schéma réels de la note 03 (constat `WEB-INJECTION-SQL`), `max_tokens = 700`, un seul llama-server par modèle.

| Modèle | Variante | Durée | finish_reason | Jetons générés | `content` (car.) | `reasoning_content` (car.) | JSON valide |
|---|---|---|---|---|---|---|---|
| minicpm5-1b-q4km | `json_schema` | 25,3 s | length | 700 | 0 | 2 537 | non |
| minicpm5-1b-q4km | `json_object` (§22) | 34,5 s | length | 700 | 0 | 2 807 | non |
| minicpm5-1b-q4km | `json_schema` + `enable_thinking: false` | 8,6 s | stop | 219 | 721 | 0 | oui |
| qwen3.5-0.8b-q4km | `json_schema` | 29,7 s | length | 700 | 0 | 2 776 | non |
| qwen3.5-0.8b-q4km | `json_object` (§22) | 32,5 s | length | 700 | 0 | 2 298 | non |
| qwen3.5-0.8b-q4km | `json_schema` + `enable_thinking: false` | 9,6 s | stop | 218 | 721 | 0 | oui |

Début de `reasoning_content` : MiniCPM5 raisonne en français (« J'apprécie cette note d'audit… »), Qwen3.5 en anglais (« Thinking Process: 1. **Analyze the Request:** … »).

En application, `waveaudit fiches` avec `mode_json = "json_object"` dans l'entrée du manifeste de MiniCPM5 : 0/2 fiches ok, 2 `repli_sortie_invalide` (« réponse du moteur : contenu non JSON »), 50 s et 55 s par fiche.

Lecture : avec `json_schema`, la sortie est vide, ce qui remplit la condition du §22. Mais la cause est la réflexion activée par défaut dans le modèle de discussion : elle consomme tout `max_tokens` avant toute réponse. Le mode `json_object` du §22 ne change rien. Seul `chat_template_kwargs = {"enable_thinking": false}` rétablit un JSON conforme.

## Correction

- §22 implémenté tel qu'écrit : `moteur.mode_json` (`json_schema` par défaut) et `mode_json` facultatif par entrée du manifeste, qui prime. En `json_object`, le schéma est ajouté en texte à la fin du message système. Aucune entrée du manifeste ne le règle : il ne corrige aucun des 4 modèles.
- Écart au §22, à entériner par Anaël : champ facultatif `reflexion` par entrée du manifeste. `false` est transmis par `moteur_openai` en `chat_template_kwargs = {"enable_thinking": false}`. S'il est absent, le corps de la requête ne change pas. Il est réglé à `false` pour `minicpm5-1b-q4km` et `qwen3.5-0.8b-q4km`.

## Tests slow

Commande : `uv run pytest -m slow -q --tb=short -p no:warnings`.

- Résultat : 2 passés en 53 s (`test_llama_reel.py` et `test_reel.py`, modèle par défaut), 648 désélectionnés.
- Aucun llama-server ne restait après l'exécution (psutil).

## Lots réels de 2 notes (après correction)

Commande : `uv run waveaudit fiches var/v1-notes --modele <nom>`, manifeste livré.

- Les notes : copies de `01-xss-reflechi.md` et `03-injection-sql.md`.
- Un seul llama-server à la fois, aucun ne restait après chaque lot (psutil). Garde réseau actif (commande `fiches` inchangée).
- « Lot total » : durée mesurée autour de la commande, démarrage d'`uv` et de llama-server compris.

| Modèle | Rôle | Lot total | Note 01 | Note 03 | JSON valide | Rubriques en français | a_revoir |
|---|---|---|---|---|---|---|---|
| granite-4.0-1b-q4km | défaut | 42,0 s | ok, 20 s | ok, 20 s | oui (2/2) | oui | 0 |
| minicpm5-1b-q4km | repli | 19,4 s | ok, 6 s | ok, 11 s | oui (2/2) | oui | 0 |
| qwen3-1.7b-q4km | candidat | 43,5 s | ok, 19 s | ok, 21 s | oui (2/2) | oui | 0 |
| qwen3.5-0.8b-q4km | candidat | 23,2 s | ok, 10 s | ok, 11 s | oui (2/2) | oui | 0 |

Avant correction (première passe, en partie pendant le téléchargement), MiniCPM5 et Qwen3.5 donnaient 0/2 fiches ok, 2 `repli_sortie_invalide` chacun, et environ 60 s par fiche.

Jetons générés par une fiche conforme : 218 et 219 (sondes ci-dessus).

## Statut par modèle

- **granite-4.0-1b-q4km (défaut) : validé.**
- **minicpm5-1b-q4km (repli) : validé** avec `reflexion = false`.
- **qwen3-1.7b-q4km (candidat) : validé.** Le préfixe `/no_think` du manifeste suffit.
- **qwen3.5-0.8b-q4km (candidat) : validé** avec `reflexion = false`.

## Observations pour V2

- Rattachement : la note 01 (XSS réfléchi) est rattachée à `WEB-XSS-STOCKE`, avec des scores BM25 très proches (55,9 contre 54,5). C'est la recherche, pas le modèle. Même résultat avec les 4 modèles.
- Les rubriques des 4 modèles restent très proches du texte du constat type : l'adaptation à la note est faible. Petites fautes d'accord (« persistent », « concatenée », « concaténé »). C'est à juger dans le banc V2.
