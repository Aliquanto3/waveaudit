---
id: C6a
title: Rapport d'incident Word
status: review
sources:
  - ../stories.yaml
  - ../SPEC.md
  - ../formats-incident.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
---

# Story C6a — Rapport d'incident Word

## Livré

- `src/waveaudit/adaptateurs/export_incident_docx.py` (nouveau) : `ExporteurIncidentDocx`
  (implémente `domaine.ports.ExporteurIncident`), constructeur `(theme_prive: Path,
  max_preuves: int = 10)`. Valide le thème privé dès la composition (`charger_theme`,
  `modele.docx` ouvert) : `ConfigurationInvalide` avant le lot, comme `ExportDocx`.
  `exporter(rapport, chemin)` écrit les 8 sections de `formats-incident.md` « Rapport
  d'incident », dans l'ordre : bandeau (en-tête/pied, première page et pages paires
  comprises), Synthèse (période, tableau des 4 sévérités `SEVERITES` avec zéros,
  hôtes touchés), Chronologie (une ligne par récit : `debut`, hôtes, `regle_titre`,
  sévérité), Faits détectés (par récit : récit, impact, recommandation, références
  ATT&CK, preuves `fichier:ligne` + message limitées à `max_preuves` avec « + N autres »,
  statut et motifs), Indicateurs de compromission (identique à
  `RapportIncident.indicateurs`), Actifs touchés, Recommandations consolidées, Annexe
  des sources (`Fichier | Enregistrements examinés | Ignorés`, mention « ligne = rang
  d'objet » pour chaque `*.json`). Sans détection (chaque liste vide) : la section
  correspondante (3 à 7) porte seulement « Aucun fait détecté », la synthèse garde son
  tableau de zéros. Écriture atomique (fichier `.partiel` puis `os.replace`),
  `PermissionError` non interceptée (comme `ExportDocx`).
- Réutilisé sans modification : `export_docx.py` (`_bandeau_en_tete_pied`, `_propre`,
  `_style_table`, importés) et `theme_generique.py` (`charger_theme`,
  `document_generique`, `assurer_styles_titre`, `appliquer_couleurs`,
  `COULEUR_PRIMAIRE_DEFAUT`, `COULEUR_SECONDAIRE_DEFAUT`).
- `tests/unitaires/test_export_incident.py` : ordre des sections, tableau des sévérités
  avec zéros, ligne de chronologie (`Fait` = `regle_titre`), tableau des indicateurs,
  limite des preuves (`+ N autres`), mention « Aucun fait détecté » sans détection
  (synthèse toujours à 4 lignes), annexe des sources avec la mention JSON, nettoyage des
  caractères interdits en XML, écriture atomique, thème privé (couleurs, modèle sans
  styles de titre) et thème privé invalide (`theme.toml`, `modele.docx`) →
  `ConfigurationInvalide`. `RapportIncident` construit en mémoire avec
  `tests/incident_outils.py` (`evenement`, `detection`, `recit`), sans dépendre de C2 à C5.

## Écarts au contrat

- `ExporteurIncidentDocx` prend `max_preuves` au constructeur (absent de la signature du
  port `exporter(rapport, chemin)` dans contrats §21) : `composition.creer_ports_incident`
  (C5) devra le passer depuis `config.incident.max_preuves` à l'instanciation, comme
  `ExportDocx` reçoit `theme_prive` au constructeur plutôt qu'à `exporter`.

## Reports

- Mention « ligne = rang d'objet » pour un fichier JSON : la section « Rapport
  d'incident » de `formats-incident.md` ne précise pas son emplacement exact (ligne de
  tableau ou texte à part). Choix pris ici : un paragraphe après le tableau, un par
  fichier `*.json`, sans l'ajouter à la cellule. À revoir si C6b ou une relecture
  manuelle du rapport de démonstration préfère une autre forme.

## Revue

- (à compléter par le second avis et le reviewer.)
