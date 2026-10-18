# Revue — story W5 (thème public et logo privé)

Base 879ffe2, commit relu cc1a787, branche `story/W5`. Relecteur : Opus, avec la liste du
second avis (Haiku). Verdict : conforme après correctifs.

Code applicatif (tokens.css, routeur du logo, `logo_present`, base.html) conforme au §28 :
logo relu à chaque requête, chemin `theme_prive` résolu contre la racine du projet, seul
`web/logo.svg` servi, CSP et nosniff posés par le middleware de W1 sur toutes les réponses
(script d'un SVG bloqué par `default-src 'self'` sans `unsafe-inline`). Écart déclaré (app.py
non touché) : accepté, la configuration est déjà dans `app.state.lots`.

| # | Sévérité | Source | Constat | Décision |
|---|---|---|---|---|
| 1 | medium | second avis | `/theme/logo.svg` absent du test CSP | corrigé : `test_logo_sous_csp_et_nosniff` (logo présent avec `<script>`, absent, tokens.css) |
| 2 | medium | second avis | aide : rôles ARIA de widget, `summary`, `contenteditable` ignorés | corrigé : XPath étendu aux rôles WAI-ARIA de widget (tab, option, checkbox…), `summary`, `[contenteditable]` |
| 3 | medium | second avis | `outline: 0`, `outline-style: none`, `outline-width: 0` non vus ; `--focus-contour` n'importe où valait remplacement | corrigé : déclarations analysées, commentaires retirés ; remplacement = `box-shadow` non nul ou `outline` avec `var(--focus-contour)` posé après |
| 4 | low | second avis | faux positifs `input type=hidden`, `label` englobant (et `img alt` dans un lien) | corrigé |
| 5 | medium (relevé de low) | second avis | `#ffffff` en dur dans style.css, contraire au §28 « couleurs par les propriétés seulement » | corrigé : token `--couleur-blanc`, test `test_style_css_sans_couleur_litterale` |
| 6 | low | second avis | `button:disabled` gris + blanc 3,4:1 | corrigé : `gris-texte` sur `fond-creme` (5,3:1, DESIGN.md) |
| 7 | low | second avis | `lxml` importé sans être déclaré (transitif via python-docx) | laissé : pyproject hors périmètre, python-docx dépendance principale ; noté dans l'aide |
| 8 | low | second avis | `id` avec guillemet → `XPathEvalError` | corrigé : variable XPath `$i` |
| 9 | medium | relecteur | test_contraste ne lisait pas DESIGN.md : une couleur décalée gardant son ratio à 0,1 près passait (vérifié : `#451DC8` passait) | corrigé : `test_tokens_css_egale_exactement_les_couleurs_de_design_md` (front matter YAML) |

Aide partagée testée par `tests/unitaires/test_aide_accessibilite.py` (38 cas acceptés ou
refusés). Complexité : 0 constat (aucune structure qui grossit). Suite complète verte.
