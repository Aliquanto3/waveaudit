# Revue — story V1 (Validation sur le vrai moteur et compatibilité JSON)

Branche revue : `story-V1-revue` (depuis `story-V1`, rebase sur `main` : déjà à jour).
Commit dev : `0e46341` (documents seulement). Socle modifié par la revue pour le seul point
autorisé par le cahier (sortie JSON : configuration, `waveaudit.toml`, manifeste, `moteur_openai`,
composition, tests).

## Constats

- high — second avis 1 — corrigé : la conclusion « json_schema fonctionne avec les 4 modèles » et
  le titre du commit contredisaient les mesures (MiniCPM5 et Qwen3.5 : `content` vide,
  `finish_reason = length`). La condition « sortie vide » du §22 est remplie. Conclusion, titre et
  statut réécrits dans `validation-moteur.md` et la story.
- medium — second avis 2 — corrigé : §22 implémenté tel qu'écrit (`moteur.mode_json`, `mode_json`
  facultatif du manifeste qui prime, `json_object` avec schéma en texte à la fin du système).
  `json_object` mesuré sur MiniCPM5 (sonde et lot réel) et Qwen3.5 (sonde) : sortie toujours vide.
  Cause réelle : réflexion par défaut. Ajout d'un champ facultatif `reflexion` au manifeste,
  transmis en `chat_template_kwargs.enable_thinking` (corps inchangé s'il est absent), réglé à
  `false` pour MiniCPM5 et Qwen3.5. **Écart au §22, à entériner par Anaël.** Le modèle de repli
  produit maintenant des fiches conformes.
- medium — second avis 3 — corrigé : suite non slow (648 passés, 2 désélectionnés), `ruff check`
  et `ruff format --check` verts, consignés ci-dessous.
- medium — second avis 4 — corrigé : les 4 lots refaits sans téléchargement concurrent ; mesures
  de la première passe remplacées.
- low — second avis 5 — corrigé : sondes brutes (finish_reason, jetons, longueurs de `content` et
  `reasoning_content`, durée) consignées en tableau.
- low — revue — reporté : workflow incident (même adaptateur) non mesuré sur MiniCPM5 et Qwen3.5.
  Vérification : `uv run waveaudit incident <dossier de démo> --modele minicpm5-1b-q4km`.
- Complexité : 0 constat (aucune structure qui grossit pendant l'exécution n'est touchée ;
  `_avec_schema_en_texte` copie la liste de 2 messages une fois par appel).

## Tests

- `uv run pytest -m slow -q --tb=short -p no:warnings` : 2 passés (53 s), aucun llama-server restant.
- `uv run pytest -q --tb=line -p no:warnings` : 648 passés, 2 désélectionnés (87 s).
- `uv run ruff check` et `uv run ruff format --check` : verts.
- Nouveaux tests (faux moteur) : corps sans `chat_template_kwargs` par défaut (clés exactes) ;
  réflexion transmise seulement si configurée ; `json_object` (format, schéma relu en JSON à la
  fin du système, liste de l'appelant intacte, cas sans message système) ; composition
  (réflexion du manifeste en local-gere, priorité du `mode_json` du manifeste, externe) ;
  manifeste (champs facultatifs, réflexion coupée sur les deux modèles seulement).

## Lots réels après correction (2 notes, manifeste livré)

| Modèle | Lot | Fiches ok |
|---|---|---|
| granite-4.0-1b-q4km | 42,0 s | 2/2 |
| minicpm5-1b-q4km | 19,4 s | 2/2 |
| qwen3-1.7b-q4km | 43,5 s | 2/2 |
| qwen3.5-0.8b-q4km | 23,2 s | 2/2 |

Verdict : prête à intégrer, sous réserve d'entériner l'écart `reflexion` au §22.
