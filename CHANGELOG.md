# Changelog

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
