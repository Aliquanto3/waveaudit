# Revue — story DOC (README et guide des testeurs)

Commit relu : 5456aaa, branche `worktree-agent-a0388b8908d827ca6`, fusionnée avec `main` (W3b
intégrée, 367bfc6) avant relecture — pas de conflit sur `README.md` ni `docs/guide-testeurs.md`.
Fichiers revus : `README.md`, `docs/guide-testeurs.md`, contre le code de `main` fusionné
(`static/relecture.js`, `templates/lot.html`, `src/waveaudit/adaptateurs/journaux.py`,
`src/waveaudit/application/composition.py`, `src/waveaudit/interfaces/cli.py`) et
`bilan-modeles.md`, `mesures-qualite.md`, `revues/story-W3b.md`, `revues/story-ARR.md`,
`revues/story-X2.md`. Aucun fichier `.py` ni gabarit modifié.

| Sévérité | Source | Constat | Décision |
|---|---|---|---|
| high | second avis 1 | guide:86 (Camille étape 2) « Ouvrez la relecture dès que la première fiche est prête » contredit `relecture.js` : l'écran de relecture ne s'affiche (`afficherRelecture`) que lorsque le lot n'est plus `en_cours` (`termine`, `echoue` ou `interrompu`), jamais sur la première fiche prête pendant que le lot tourne. | Corrigé : étape reformulée (« Attendez la fin du lot... l'écran de relecture s'affiche alors automatiquement »). |
| high | second avis 2 | README:90-103 et guide:76-104, écrits avant W3b : tiroir, candidats, `Ctrl+Alt+↓`, « Exporter un brouillon », « Enregistré » à vérifier contre le code réel. | Vérifié un par un contre `relecture.js` et `lot.html` : raccourci `Ctrl+Alt+↓`/`↑` (ligne 1249-1253), bouton `#bouton-exporter-brouillon` libellé « Exporter un brouillon », indicateur « Enregistrement… » puis « Enregistré », tiroir (`listbox`/`option`), barre de candidats (`tablist`) — tous conformes, aucune correction de libellé nécessaire. Seul le point 1 (timing d'ouverture) était faux, déjà corrigé ci-dessus. |
| medium | second avis 3 | README:217-218 « rang 1 atteint 8 fois sur 9 et 9 fois sur 9 » confond top1 et top3 ; `bilan-modeles.md:115-116` donne top1 = 8/9, top3 = 9/9 (rang 1 à 3 inclus pour le top3, pas le rang 1 seul). | Corrigé : reformulé en distinguant top1 (rang 1, 8/9) et top3 (dans les 3 premiers, 9/9). |
| medium | second avis 4 | guide:115 (Karim étape 4) proposait un dossier vide (bloqué par `required`, impossible à déposer) ou un `.csv`, qui est un journal reconnu (`router_journal` route `.csv` vers `"csv"`, vérifié : `journal_reconnu('notes.csv')` → `True`). | Corrigé : étape remplacée par un fichier `notes.txt` réel, vérifié non reconnu (`journal_reconnu('notes.txt')` → `False`, ni `.json`, ni `.csv`, ni préfixe/suffixe `.log`). |
| medium | second avis 5 | guide:107 (Karim étape 1) « déposez le dossier donnees/demo/incident » : le champ `journaux` de `index.html` est `<input type="file" multiple>`, pas un sélecteur de dossier. | Corrigé : étape reformulée pour lister les fichiers à sélectionner (`auth.log`, `syslog`, `security.json`, `system.json`, `sysmon.csv`). |
| medium | second avis 6 | guide:94 (Camille étape 5) « sur une entrée non rattachée (si le lot en produit une) » : `tests/unitaires/test_notes.py::test_les_30_notes_de_demonstration_sont_rattachables` prouve qu'aucune des 30 notes fournies ne donne `non_rattachee` ; l'étape n'était donc jamais reproductible avec le jeu livré. | Corrigé : étape reformulée pour ajouter une note hors sujet (ex. une recette, cf. `tests/donnees/notes/hors-sujet.md`, utilisée par `test_note_hors_sujet_non_rattachee_sans_requete`), qui donne bien `non_rattachee` sans appel au modèle (score BM25 maximal ≤ 0). |
| low | second avis 7 | Libellés « Génération en cours », « Enregistrement… », « Exporter un brouillon » à vérifier contre le code. | Vérifié conformes (voir constat high 2) ; aucune correction. |
| low | second avis 8 | Limites manquantes : borne d'arrêt de l'UI non garantie à 10 s hors Windows (`revues/story-ARR.md`, second avis 6) ; régénération d'un lot depuis une autre instance de l'UI non détectable (`revues/story-X2.md`, second avis 2). | Corrigé : deux puces ajoutées à « Limites du POC » du README. |
| low | second avis 9 | Seuil de repli modèle (`ram_min_defaut_go` = 4,5 Go, `composition.py:47-51` et `config/waveaudit.toml`) absent du README, et non remesuré en v2. | Corrigé : phrase ajoutée à la section « Choix et licences des modèles », précisant le seuil et qu'il n'a pas été remesuré en v2. |
| low | second avis 10 | `_bmad-output/specs/spec-waveaudit-v2/stories/story-DOC-documentation-v2.md:113` « incident ne connaît pas --annee » est faux : `cli.py` définit bien l'option `--annee` (défaut : année courante si absente). | Corrigé dans le fichier de spec : formulation reprise pour dire explicitement que `--annee` existe, avec sa valeur par défaut, et note que la formulation précédente était ambiguë/fausse telle que lue. |
| — | reviewer | Section « Points à vérifier en recette » du guide incomplète au regard de `revues/story-W3b.md` (« Reste pour la REC ») : manquaient l'indicateur Enregistrement…/Enregistré et ses annonces `aria-live`, le conflit à deux onglets (Échap, Garder ma version, Recharger), le serveur arrêté pendant une saisie, le détail de la confirmation de changement de candidat sur fiche corrigée, l'export brouillon par `Blob`, le lien « Télécharger le rapport », l'opacité des dialogues, et le piège de focus Tab. | Corrigé : puces ajoutées, sans doublon avec les points déjà présents (bascule de workflow, parcours clavier, `lang`, confirmations, arrêt UI, repli RAM, repli du tiroir sous 1440 px). |
| — | reviewer | Complexité : 0 constat. Story de documentation seule, aucune structure de code modifiée. | — |

## Points vérifiés conformes, sans correction

- `uv run python -c "from waveaudit.application.composition import journal_reconnu; print(journal_reconnu('notes.txt'))"` → `False` ; `journal_reconnu('notes.csv')` → `True`.
- `src/waveaudit/interfaces/cli.py:184-235` : `incident` définit `--annee` (`typer.Option(None, "--annee", ...)`, défaut `datetime.now().year`).
- `src/waveaudit/domaine/configuration.py:37` et `config/waveaudit.toml:18` : `ram_min_defaut_go = 4.5`.
- `_bmad-output/implementation-artifacts/bilan-modeles.md:114-116` : top1 = 18/20 (01-20), top1 = 8/9 et top3 = 9/9 (21-28, 30).
- `tests/unitaires/test_notes.py::test_les_30_notes_de_demonstration_sont_rattachables` et `tests/unitaires/test_pipeline.py::test_note_hors_sujet_non_rattachee_sans_requete`.

Tests : documentation seule, aucun test de code à relancer. Contrôle rapide
`uv run --no-sync python .claude/cost-kit/controle_rapide.py` lancé après corrections.
