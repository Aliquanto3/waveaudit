# Changelog

## 0.2.0-rc.3 (0.2.0rc3)

### Contenu

- **Charte générique v2.1** : jetons de `dist/charte.css` dans `tokens.css`, thème sombre par défaut,
  clair sous `prefers-color-scheme: light`, `data-theme` pour forcer l'un ou l'autre. Pas de
  sélecteur de thème dans l'interface.
- **Interface web** : bouton principal neutre (`bouton`), boutons secondaires en contour `trait-fort`,
  boutons à bascule neutres (jamais de bleu en aplat), focus `focus`, liens soulignés, filet or sous le
  titre de page, favicon et pictogramme de la charte, champs de formulaire stylés dans les deux
  thèmes. Polices Sora 600, Atkinson Hyperlegible et JetBrains Mono servies localement
  (`static/polices/`, licences OFL jointes).
- **Rapport Word générique** : titres en `Sora SemiBold` et texte en `Atkinson Hyperlegible` (noms
  Office de la charte), titres en `primaire` et sous-titres en `texte-attenue` (thème Office clair),
  filet or (`accent`, 3 pt) sous le titre du document.
  Un `modele.docx` privé garde ses propres polices.
- **Tests** : `test_contraste.py` réécrit (couples explicites dans les deux thèmes, 4,5:1 pour le
  texte, 3:1 pour `trait-fort`, `focus` et les marques non textuelles ; pas de bleu en aplat de
  bouton ; pas de couleur littérale hors `tokens.css`). Tests d'export réalignés.
- Captures : `docs/media/charte-v2/` (accueil et lots, clair et sombre).

### Limites

- Les polices ne sont pas incorporées au .docx (odttf) : sans Sora ni Atkinson installées, Word se
  replie sur sa police par défaut ; le repli de la charte (Segoe UI Semibold pour les titres, Segoe UI
  pour le texte) se choisit à la main. L'incorporation demande de copier `incorporer.py` de la charte avec
  ses dépendances (jetons, lecture des tables TTF) : reportée.
- Le thème Office embarqué du .docx (`theme1.xml` du gabarit python-docx) n'est pas remplacé par
  `theme-office.xml` de la charte : les styles employés portent des couleurs et polices explicites,
  les autres gardent celles du gabarit.
- Pas de capture de la page de relecture ni de la page incident (elles demandent un lot produit par
  un moteur).
- `_bmad-output/planning-artifacts/ux/DESIGN.md` et la maquette décrivent encore l'ancienne palette :
  historique, non réaligné.
- Le chemin de configuration obsolète `waveaudit.local.toml` reste lu (compatibilité, 0.2.0-rc.2).

## 0.2.0-rc.2 (0.2.0rc2)

- **Changement de nom** : le projet `waveaudit` (WaveAudit) devient `pentest-scribe`
  (PentestScribe). Paquet Python `pentest_scribe`, commande `pentest-scribe` (pas d'alias de
  l'ancienne commande), dépôt `Aliquanto3/pentest-scribe`. Les anciens liens GitHub
  `Aliquanto3/waveaudit` sont redirigés par GitHub.
- **Charte générique** : palette bleu pétrole et orange brûlé aux contrastes WCAG AA mesurés
  (`tokens.css`, `DESIGN.md`, maquette), polices système, pictogramme SVG et nom affiché en texte
  dans l'en-tête. Le jeton `--couleur-fond-creme` devient `--couleur-fond` ; nouveau jeton
  `--couleur-focus`. Le dépôt public ne fournit plus de logo ; un logo facultatif reste possible par
  `theme-prive/web/logo.svg`.
- **Migration** : le fichier de configuration `config/waveaudit.toml` devient
  `config/pentest-scribe.toml`. La surcharge locale `waveaudit.local.toml` est encore lue si
  `pentest-scribe.local.toml` est absent, avec un avertissement de dépréciation ; la renommer.
  Le projet n'utilise ni variable d'environnement ni dossier de données utilisateur : rien d'autre
  à migrer.
- Références de marque et informations internes retirées des documents de spécification.

## 0.2.0-rc.1

Version candidate de la v2 (relecture web, workflow incident), sous le nom `waveaudit`.
