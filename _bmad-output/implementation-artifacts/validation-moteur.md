# Validation sur le vrai moteur (story V1)

Mesures brutes du 2026-10-18, sur le poste de développement. Ce n'est pas l'EliteBook cible.

## Machine (psutil et Win32_Processor)

- Processeur : 11th Gen Intel Core i5-1145G7 à 2,60 GHz, 4 cœurs physiques, 8 logiques.
- RAM : 15,7 Gio au total, 7,3 Gio disponibles pendant les lots.
- Windows 11 Entreprise. llama-server b11714 en CPU, `threads = 4`, `ctx = 4096`.
- Configuration livrée : `temperature = 0.2`, `seed = 42`, `max_tokens = 700`.

## Installation

- Commande : `uv run waveaudit installer --candidats`, lancée depuis le dépôt principal.
- Durée : 6 min 15 s pour environ 3,4 Go, d'une traite, sans reprise.
- Empreintes SHA-256 : toutes conformes au manifeste (moteur et 4 modèles).
- Archive llama-server : `llama-server.exe` est à la racine du zip. `executable` reste inchangé dans `config/artefacts.toml`.
- Le worktree pointe sur `var/` du dépôt principal par un `waveaudit.local.toml` ignoré par git (`[chemins] var = "<dépôt>/var"`). Les modèles n'ont pas été copiés.

## Tests slow

Commande : `uv run pytest -m slow -q --tb=short -p no:warnings`.

- Résultat : 2 passés en 49 s (`test_llama_reel.py` et `test_reel.py`, sur le modèle par défaut).
- Aucun llama-server ne restait après l'exécution (vérifié avec psutil).

## Lots réels de 2 notes

Commande : `uv run waveaudit fiches var/v1-notes --modele <nom>`.

- Les notes : copies de `01-xss-reflechi.md` et `03-injection-sql.md`.
- Un seul llama-server à la fois. Aucun ne restait après chaque lot (psutil).
- Les lots de granite et de MiniCPM ont tourné pendant la fin du téléchargement.

| Modèle | Rôle | Lot total | Note 01 | Note 03 | JSON valide | Rubriques en français | a_revoir |
|---|---|---|---|---|---|---|---|
| granite-4.0-1b-q4km | défaut | 46 s | ok, 23,0 s | ok, 20,3 s | oui (2/2) | oui | 0 |
| minicpm5-1b-q4km | repli | 2 min 08 | a_revoir, 62,3 s | a_revoir, 63,4 s | non (0/2, 2 essais par note) | sortie de repli (catalogue) | 2 : `repli_sortie_invalide` |
| qwen3-1.7b-q4km | candidat | 41 s | ok, 17,9 s | ok, 19,4 s | oui (2/2) | oui | 0 |
| qwen3.5-0.8b-q4km | candidat | 2 min 00 | a_revoir, 56,9 s | a_revoir, 60,4 s | non (0/2, 2 essais par note) | sortie de repli (catalogue) | 2 : `repli_sortie_invalide` |

Le détail de chaque motif `repli_sortie_invalide` est « réponse du moteur : contenu non JSON ».

Débit de génération, d'après les journaux de llama-server :
- granite : 12 à 14 jetons/s ;
- qwen3-1.7b : 13 à 14 jetons/s ;
- minicpm5 : 23 jetons/s.

Fiches ok : environ 205 à 220 jetons générés par fiche.

## Diagnostic des échecs (sonde brute, hors application)

Une sonde a appelé `/chat/completions` directement, avec le prompt et le schéma réels de la note 03.

- Avec `json_schema`, MiniCPM5 et Qwen3.5 renvoient `content` vide et `finish_reason = length`. Les 700 jetons partent dans `reasoning_content` : leur modèle de discussion active la réflexion (« thinking ») par défaut.
- Avec `json_object` (§22, schéma en texte à la fin du message système), Qwen3.5 donne le même résultat : `content` vide, `length`, réflexion. Le mode §22 ne corrige donc pas ces échecs.
- Avec `/no_think` en préfixe système, MiniCPM5 donne le même résultat : il raisonne en anglais. Le préfixe ne suffit pas pour ce modèle.
- Avec `chat_template_kwargs = {"enable_thinking": false}` dans la requête et `json_schema`, les deux modèles rendent un JSON conforme : `finish_reason = stop`, environ 220 jetons, en 9 à 11 s, rubriques en français.

**Conclusion : `json_schema` fonctionne avec les 4 modèles.** La condition de §22 (grammaire refusée, ou sortie vide ou non conforme à cause de `json_schema`) n'est pas remplie. `mode_json` n'a donc pas été ajouté.

## Statut par modèle

- **granite-4.0-1b-q4km (défaut) : validé.**
- **qwen3-1.7b-q4km (candidat) : validé.** Le préfixe `/no_think` du manifeste suffit.
- **minicpm5-1b-q4km (repli) : non validé.** Ses fiches passent toutes en repli tant que la réflexion n'est pas coupée.
- **qwen3.5-0.8b-q4km (candidat) : non validé**, pour la même cause.

## Observations pour V2

- Rattachement : la note 01 (XSS réfléchi) est rattachée à `WEB-XSS-STOCKE`, avec des scores BM25 très proches (55,9 contre 54,5). C'est la recherche, pas le modèle. Même résultat avec les 4 modèles.
- Les rubriques de granite et de qwen3 restent très proches du texte du constat type : l'adaptation à la note est faible. C'est à juger dans le banc V2.
