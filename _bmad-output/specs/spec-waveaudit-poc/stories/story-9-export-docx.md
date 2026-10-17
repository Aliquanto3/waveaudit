---
id: story-9
title: Export Word et thèmes
status: review
sources:
  - ../stories.yaml
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/ARCHITECTURE-SPINE.md
---

# Story 9 — Export Word et thèmes

## Livré

- `src/waveaudit/adaptateurs/theme_generique.py` (AD-14) :
  - `document_generique() -> Document` : `Document()` vierge stylé de façon neutre (pas de
    charte, pas de logo), couleurs par défaut sur `Title`/`Heading 1`/`Heading 2`/`Heading 3`.
  - `appliquer_couleurs(document, couleur_primaire, couleur_secondaire)` : colore les styles de
    titre existants ; un style absent (modèle privé qui ne les définit pas) est ignoré.
  - `charger_theme(dossier_theme_prive) -> dict` : lit `theme.toml` s'il existe
    (`couleur_primaire`, `couleur_secondaire`, `logo` relatif au dossier et devant exister) ;
    `{}` si absent ; toute clé inconnue est ignorée.
- `src/waveaudit/adaptateurs/export_docx.py` (CAP-6, contrats §17, AD-14), implémente le port
  `domaine.ports.Exporteur` :
  - `BANDEAU = "Démonstration — données fictives"`, constante publique réutilisable par le futur
    export incident (CERT, contrats §21) sans modifier ce module.
  - `ExportDocx(theme_prive: Path)` : `exporter(rapport, chemin)` part de
    `theme_prive/modele.docx` s'il existe, sinon du thème générique ; applique les couleurs de
    `theme.toml` si présentes ; écrit le bandeau exact en en-tête et en pied de chaque section ;
    crée les dossiers parents de `chemin` si besoin.
  - Structure exacte du contrat : titre `Rapport de constats`, table de synthèse
    `N° | Titre | Sévérité | Score | Statut`, puis par fiche un titre `N. <titre>` et les
    intitulés `Description`, `Impact`, `Recommandation`, `CVSS 3.1`, `Références`, `Statut`,
    `Traçabilité` ; sévérité affichée parmi `Aucune/Faible/Moyenne/Élevée/Critique` ; statut
    `OK` ou `À revoir` suivi des motifs `code : detail` ; annexe `Annexe — notes écartées`
    (tableau `Note | Statut | Motif`) seulement si `rapport.ecartees` n'est pas vide.
- `tests/unitaires/test_export_docx.py` : rapport construit à la main (2 fiches dont une
  `a_revoir` avec motifs, 2 écartées), relu avec python-docx :
  - bandeau en en-tête et en pied de chaque section, titres et intitulés exacts, table de
    synthèse et ses valeurs, motifs affichés, annexe présente seulement si des entrées sont
    écartées (test séparé sans écartées : pas de titre d'annexe, une seule table) ;
  - thème privé : `modele.docx` et `theme.toml` (avec `couleur_primaire` et une clé inconnue)
    créés sous `tmp_path/theme-prive`, couleur du style `Heading 1` relue dans le `.docx`
    produit ; sans `theme-prive/`, le thème générique fonctionne (deux autres tests).

## Écarts au contrat (variantes minimales)

- Le contrat ne fixe pas le texte exact des paragraphes de contenu (`CVSS 3.1`, `Traçabilité`,
  `Références`) au-delà de leur composition (« vecteur, score, sévérité », « id — titre — url »,
  « note, constat type ») : choisi un format lisible à un seul paragraphe par rubrique
  (`"Vecteur : … — Score : … — Sévérité : …"`, `"Note : … — Constat type : …"`), une ligne par
  référence. Pas de divergence sur les éléments testables (intitulés, table, bandeau, statut).
- Colonne `Statut` de l'annexe : valeur brute de l'énumération (`non_traitee`/`non_rattachee`),
  faute de libellé imposé par le contrat ou `formats.md`.
- `theme.toml.logo` est lu et validé (chemin relatif existant) mais non encore inséré dans le
  document : reporté ci-dessous, la story ne précise pas d'emplacement.

## Reports

- Insertion du logo du thème privé dans l'en-tête ou la page de garde : `charger_theme` le
  valide déjà (chemin relatif à `theme-prive/`, doit exister) mais `ExportDocx` ne le dessine
  pas encore, faute d'emplacement imposé par contrats §17. À faire avec la story qui fournira un
  `theme-prive/` réel de démonstration, ou sur demande explicite.
- Câblage dans `application/lot.py` (étape 5 : `exporter` vers `rapport.docx`, copie vers
  `copie_rapport`) : hors périmètre de cette story, qui livre l'adaptateur seul ; dépend de la
  story qui assemble le lot complet.

## Revue

- Contrôle rapide (`uv run --no-sync python .claude/cost-kit/controle_rapide.py`) : aucune
  erreur.
- Suite complète (`uv run pytest -q --tb=line -p no:warnings`) : 168 tests passés.

Revue (détail : `_bmad-output/implementation-artifacts/revues/story-9.md`) :
- medium, second avis 1 : caractères hors XML (`\x00`) faisaient échouer l'export — corrigé (`_propre`).
- medium, second avis 2 : couleur invalide → `ValueError` — corrigé, `ConfigurationInvalide` dès `ExportDocx(...)`.
- low, second avis 3 : couleur à 5 chiffres acceptée — corrigé (`#RRGGBB` strict).
- medium, second avis 4 : modèle sans styles `Title`/`Heading N` → `KeyError` — corrigé (styles ajoutés).
- low, second avis 5 : `theme.toml` mal formé, `modele.docx` illisible — corrigé, `ConfigurationInvalide`.
- low, second avis 6 : écriture non atomique — corrigé (`.partiel` puis `os.replace`).
- low, second avis 7 : bandeau absent en-tête de première page / pages paires — corrigé.
- medium, revue : le bandeau écrasait l'en-tête du modèle (logo, mentions) — corrigé, paragraphe ajouté.
- low, second avis 8 : tests manquants (`config.chemins.theme_prive`, styles du modèle) — corrigé.
- low, dev : logo non inséré — reporté (emplacement non fixé par §17) ; câblage `lot.py` — reporté.
- Écart consigné : thème privé invalide → `ConfigurationInvalide` (code 2) plutôt que repli silencieux.
- Complexité : 0 constat (export linéaire, 400 fiches en 3,8 s).
