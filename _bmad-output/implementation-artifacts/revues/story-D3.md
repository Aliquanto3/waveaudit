# Revue — story D3 (Guide des testeurs et formulaire de retour)

Branche revue : `story-D3-revue` (depuis `story-D3`, rebase sur `main` : trivial, déjà à jour).
Commit dev : `cd7517f`. Story documentaire ; aucun fichier de `src/` ni `tests/` touché.

## Revue

- medium — second avis — corrigé : `docs/guide-testeurs.md` ne mentionnait pas `waveaudit sbom`
  dans « Ce qui sort, ou non, du poste ». Vérifié que `sbom` (src/waveaudit/installation/sbom.py)
  ne fait aucun appel réseau (lecture du venv local uniquement, pas de `garde()`). Ajouté une
  phrase dédiée, distincte du garde réseau qui protège `fiches`/`ui`/`banc`.
- low — second avis — corrigé : l'UI (`src/waveaudit/interfaces/web/templates/index.html`,
  `<input type="file" ... multiple>`) prend des fichiers, pas un dossier. Guide corrigé
  (« un ou plusieurs fichiers `.md`/`.txt` (pas un dossier) »).
- low — second avis — corrigé : « chaque fiche se génère en arrière-plan » est vrai pour l'UI
  (`threading.Thread` dans `src/waveaudit/interfaces/web/app.py`) mais pas pour la CLI `fiches`,
  qui traite les notes de façon synchrone dans le terminal (`src/waveaudit/interfaces/cli.py`,
  pas de thread/async). Reformulé : section CLI dit « synchrone », la mention « en arrière-plan »
  déplacée dans la section UI où elle est vraie.
- low — second avis — corrigé : incohérence entre « traitez-en quelques-unes (copiez-les à part) »
  et la commande donnée qui traite tout `donnees/demo/notes` (30 notes, vérifié par `ls`).
  Reformulé : la commande du guide traite le dossier complet par défaut, avec la variante
  « quelques notes » proposée comme option explicite (pointer la commande sur un sous-dossier).
- low — second avis — corrigé : l. 23 « rien d'autre n'est appelé sur le réseau » pour `uv sync`
  contredisait la section réseau plus bas, qui liste `uv sync` comme appelant l'extérieur (PyPI).
  Reformulé pour dire explicitement que `uv sync` télécharge les paquets Python figés depuis
  PyPI, sans autre dépôt ni télémétrie.
- low — second avis — corrigé : le guide parlait d'une « entrée écartée » pour une note invalide,
  alors que le rapport Word affiche la section « Annexe — notes écartées » (vérifié dans
  `src/waveaudit/adaptateurs/export_docx.py`, fonction `_annexe_ecartees`). Reformulé pour
  renvoyer vers ce libellé exact.

## Vérifications

- `uv run ruff check` et `uv run ruff format --check` : verts (aucun fichier de code modifié).
- `uv run pytest -q --tb=line -p no:warnings` : 283 passed, 2 deselected.
- Guide relu après corrections : toujours une page et demie environ (105 lignes Markdown,
  +3 lignes vs la version dev).
- Aucun écart au contrat de la story D3 à signaler ; `README.md` et
  `.github/ISSUE_TEMPLATE/retour-testeur.md` non modifiés par cette revue (non mis en cause par
  le second avis, relecture rapide ne montrant pas d'incohérence avec le code).

## Verdict

Prête à intégrer.
