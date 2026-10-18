---
id: W5
title: Thème public et logo privé de l'interface
status: review
sources:
  - ../stories.yaml
  - ../SPEC.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/impacts-v2.md
  - ../../../planning-artifacts/ux/DESIGN.md
---

# Story W5 — Thème public et logo privé

## Livré

- `interfaces/web/static/tokens.css` (nouveau) : propriétés `--couleur-<nom>` pour chaque
  couleur de `DESIGN.md` (palette officielle Wavestone, y compris les rôles dérivés
  `*-texte`), `--focus-contour` / `--focus-decalage`, `--police-texte` /
  `--police-chasse-fixe` / `--taille-<niveau>`. Valeurs exactes de `DESIGN.md`.
- `interfaces/web/static/style.css` : couleurs exprimées uniquement par ces propriétés (plus
  de couleur en dur) ; en-tête (`.en-tete`, logo optionnel), bandeau, boutons, focus clavier
  via `:focus-visible` + `--focus-contour` (aucun `outline: none`) ; aucune `@font-face`,
  aucun `url()` hors `/static/` ou `/theme/` ; `prefers-reduced-motion` respecté.
- `interfaces/web/templates/base.html` : en-tête avec `<img class="en-tete-logo"
  src="/theme/logo.svg" alt="">` affiché seulement si `logo_present`, bandeau déjà en haut et
  en bas (hérité de W1).
- `interfaces/web/commun.py` : `chemin_logo(request)` (chemin du logo privé, via
  `request.app.state.lots.config.chemins.theme_prive`, déjà posé par W1 — aucun ajout à
  `app.py`) ; `page()` calcule `logo_present` par `is_file()` à chaque rendu.
- `interfaces/web/routeurs/theme.py` : `GET /theme/logo.svg` sert le fichier s'il existe
  (`FileResponse`, `image/svg+xml`), sinon 404 `logo_absent`. Rien d'autre de `theme-prive/`
  n'est servi.
- `tests/accessibilite.py` (nouveau, aide partagée, `lxml.html`/`xpath`, sans `cssselect`) :
  `verifier_accessibilite(html)` (nom accessible de tout élément interactif, aucun `tabindex`
  positif, dialogues `aria-modal`/`aria-labelledby`, `id` référencés existants) et
  `verifier_focus_css(css)` (`:focus-visible` avec `--focus-contour`, aucun `outline: none`
  sans contour de remplacement).
- `tests/unitaires/test_contraste.py` (nouveau) : relit les couleurs de `tokens.css`, recalcule
  chaque ratio WCAG 2.1 des paires déclarées dans `DESIGN.md` (palette, rôles dérivés, table de
  sévérité CVSS), vérifie le seuil (4,5 texte, 3 focus) et l'égalité à 0,1 près avec le ratio
  annoncé par `DESIGN.md`.
- `e2e/test_ui.py` : nouveaux `test_logo_200_ou_404_selon_theme_prive`,
  `test_logo_present_dans_le_html` (deux `theme_prive` sous `tmp_path`),
  `test_accessibilite_accueil` (accueil et page de suivi, plus `verifier_focus_css` sur
  `style.css`). `test_bandeau_sur_chaque_page`,
  `test_aucune_url_externe_dans_templates_et_static`, `test_pages_portent_le_jeton_sans_script_ni_style_en_ligne`
  et `test_csp_et_nosniff_sur_chaque_reponse` restaient verts sans modification.

## Choix d'interprétation

- Pas d'ajout à `interfaces/web/app.py` : l'accès à la configuration depuis `theme.py` et
  `commun.page()` réutilise `request.app.state.lots.config`, déjà posé par `creer_app` (W1).
  Le commentaire de collision de `stories.yaml` (« app.py W1 puis W5, W2 ») et la ligne 30
  d'`impacts-v2.md` citent `app.py` parmi les fichiers touchés par cette story, mais la liste
  « Fichiers » de l'entrée W5 ne le mentionne pas, et le docstring de `creer_app` interdit
  explicitement toute nouvelle story web de le retoucher (AD-22 [revue A28]). Retenu : aucun
  changement à `app.py`, écart consigné ici plutôt que rouvert.
- `tests/accessibilite.py` écrit sans `cssselect` (absent des dépendances) : sélection des
  éléments interactifs par XPath seulement (`//a[@href] | //button | //input | //select |
  //textarea | //*[@tabindex]`), équivalent au sélecteur CSS du contrat.
- Paires texte/fond de `test_contraste.py` : la liste des rôles dérivés et de la table de
  sévérité CVSS de `DESIGN.md`, plus `primaire`/blanc et `primaire`/`primaire-doux` (actions
  principales) et le blanc du bandeau sur `primaire-fonce`. Les couleurs de marque jamais
  utilisées seules en texte (`accent`, `attention`, `danger`, `gris`) ne sont pas incluses
  comme « texte » : elles ne portent pas de paire de contraste annoncée par `DESIGN.md`.
- Focus clavier : aucun `outline: none` écrit nulle part (le focus repose entièrement sur
  `:focus-visible` + `--focus-contour`), ce qui satisfait trivialement la règle « aucun
  `outline: none` sans contour de remplacement ».

## Reports

- Tiroir, onglets des candidats, boîtes de dialogue et leurs rôles ARIA concrets : W3b
  (fiche de relecture) et W4 (incident), qui réutilisent `tests/accessibilite.py` tel que
  livré ici.
- Bandeau et CSP sur `/lots`, `/incidents/{id}` (pages pas encore créées) : W2 et W4.
- Logo et modèle Word de marque : `theme-prive/` (ignoré par git), rien dans ce commit.

## Revue

Tests ciblés et suite complète (`825 passed`) verts, `ruff check` et `ruff format --check`
propres, contrôle rapide sans erreur. Complexité : 0 constat.

Revue Opus (détail : `implementation-artifacts/revues/story-W5.md`) : 5 medium corrigés (CSP du
logo, rôles ARIA de l'aide, retrait de contour CSS, `#ffffff` en dur, parité exacte tokens.css
et DESIGN.md), 3 low corrigés (faux positifs, bouton désactivé, id à guillemet), 1 low laissé
(`lxml` transitif, pyproject hors périmètre). Complexité : 0 constat.
