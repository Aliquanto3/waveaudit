---
id: DOC-T
title: Guide des testeurs réorganisé pour des collègues auditeurs
status: review
sources:
  - ../stories.yaml
  - ../SPEC.md
  - ../../../implementation-artifacts/recette-v2.md
  - story-DOC-documentation-v2.md
  - story-W1-socle-web.md
  - story-W3b-ecran-relecture.md
  - story-W4-incident-dans-l-ui.md
---

# Story DOC-T — Guide des testeurs réorganisé pour des collègues auditeurs

Pas de code. Réorganise `docs/guide-testeurs.md` pour un public non développeur (collègues
auditeurs cyber, PC Wavestone Windows 11, réseau d'entreprise), met à jour `README.md` et le
modèle d'issue `.github/ISSUE_TEMPLATE/retour-testeur.md`. Rien d'autre modifié.

## Livré

### `docs/guide-testeurs.md`

- **« En bref, ce que vous pouvez faire »** en tête (8 puces) : déposer des notes fictives et
  obtenir des fiches de vulnérabilité ; relire chaque fiche à côté de sa note, corriger,
  valider ; changer le constat type proposé ou en choisir un à la main ; exporter un brouillon
  à tout moment ou le rapport Word final ; travailler en français ou en anglais ; analyser des
  journaux et obtenir un rapport d'incident (démo CERT) ; tout reste sur le poste.
- **Prérequis** complétés : installation de uv sans droits admin (script PowerShell officiel ou
  `winget`), `uv python install 3.12` (le projet épingle `requires-python = "==3.12.*"`, `uv
  sync` installe Python 3.12 au besoin), git facultatif (ZIP GitHub). Espace disque : ~1,6 Go
  pour l'installation par défaut (moteur + modèle par défaut + repli,
  `config/artefacts.toml`), ~3,3 Go avec les modèles candidats (`installer --candidats`) ;
  3 Go recommandés par prudence.
- **Réseau d'entreprise** (nouvelle sous-section) : seules `uv sync` et `waveaudit installer`
  sortent ; proxy via `HTTPS_PROXY` ; `--native-tls`/`UV_NATIVE_TLS=1` si le proxy inspecte TLS
  (uv) ; `waveaudit installer` utilise `httpx.Client(trust_env=True)`
  (`telechargement.py`), donc `HTTPS_PROXY`/`HTTP_PROXY` suffisent, `SSL_CERT_FILE` si besoin
  d'un certificat d'entreprise. Domaines contactés : `github.com` (moteur llama.cpp) et
  `huggingface.co` (modèles), lus dans `config/artefacts.toml`.
- **Premier essai dans l'interface** avant la CLI : `uv run waveaudit ui`,
  `http://127.0.0.1:8765`, workflow « Fiches », dépôt de 3-4 notes nommées
  (`01-xss-reflechi.md`, `02-xss-stocke.md`, `03-injection-sql.md`), suivi de la progression,
  écran de relecture, correction/validation, export. Raccourcis `Ctrl+Entrée` (valider),
  `Ctrl+Alt+↓`/`↑` (naviguer), vérifiés dans `relecture.js`. Parcours de Camille et de Karim
  conservés en détail, reformulés pour un public non développeur.
- **CLI** devenue section « Pour aller plus loin » (lot complet, `--langue en`, `exporter`).
- **Retrait** de « Points à vérifier en recette » (reste propre à `recette-v2.md`, déjà
  existant, destiné au mainteneur). Conservés : « Si c'est lent ou bloqué » (ajout : repli
  automatique sur un modèle plus petit sous 4,5 Go de RAM libre, `ram_min_defaut_go`,
  annoncé à l'accueil de l'UI), « Ce qui sort, ou non, du poste », « Votre retour » (issue
  GitHub, repli par mail si pas de compte GitHub, rappel : jamais de données réelles de
  mission).
- Vocabulaire interne retiré des parties destinées aux testeurs (pas de « §», « contrats »,
  « story », « CAP-x », « BM25 »).

### `README.md`

- Section **« Ce que fait WaveAudit »** (6 puces, usage) juste après l'intro, suivie du renvoi
  au guide des testeurs (bloc « Vous testez le POC ? » remonté ici).
- État mis à jour : « POC v2 en test (version candidate 0.2.0) ».
- Prérequis/Installation alignés sur le guide : uv sans droits admin, ZIP possible sans git,
  proxy en une phrase avec renvoi au guide. Reste du README (technique) inchangé.

### `.github/ISSUE_TEMPLATE/retour-testeur.md`

- En-tête YAML conservée (name, about, labels: retour-testeur).
- Ajouts : version testée (`uv run waveaudit version`), installation (durée, proxy/blocage),
  interface (relecture, correction, changement de candidat, export brouillon/final), langue
  utilisée, démo incident (si testée), idées et constats types manquants. Grille des fiches
  (utilisable / retouches légères / à refaire) conservée.

## Vérifications faites

- `requires-python = "==3.12.*"` (`pyproject.toml`) : `uv python install 3.12` et `uv sync`
  couvrent l'installation de Python par uv.
- Domaines et tailles des artefacts dans `config/artefacts.toml` (moteur `github.com`, modèles
  `huggingface.co` ; tailles sommées pour l'estimation d'espace disque).
- `trust_env=True` dans `src/waveaudit/installation/telechargement.py` (docstring de module :
  seul module à faire ces appels, proxy d'entreprise laissé passer).
- `ram_min_defaut_go = 4.5` dans `config/waveaudit.toml`.
- Raccourcis clavier (`Ctrl+Entrée`, `Ctrl+Alt+↓`/`↑`) relus dans
  `src/waveaudit/interfaces/web/static/relecture.js` (lignes ~1244-1253).
- Noms de workflows « Fiches »/« Incident » et langues « Français »/« English » relus dans
  `src/waveaudit/interfaces/web/templates/index.html`.
- Notes `donnees/demo/notes/01-xss-reflechi.md`, `02-xss-stocke.md`, `03-injection-sql.md` :
  fichiers existants (listing du dossier).
- `_bmad-output/implementation-artifacts/recette-v2.md` existe déjà : destination confirmée
  pour les points de recette retirés du guide.

## Écarts

- Aucun écart constaté au périmètre demandé.

## Revue

- (à compléter par le second avis et le reviewer)
