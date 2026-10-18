---
name: WaveAudit
description: Application web de bureau pour l'audit cyber hors ligne (relecture des fiches générées, workflow incident CERT). Rendu serveur Jinja + JS sans framework, servie sur 127.0.0.1.
status: final
updated: 2026-10-18
sources:
  - _bmad-output/planning-artifacts/ux/.memlog.md
  - _bmad-output/specs/spec-waveaudit-v2/arbitrages.md
  - _bmad-output/planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
colors:
  primaire: '#30507D'
  primaire-fonce: '#1C2E47'
  primaire-doux: '#E3E9F0'
  accent: '#2F6657'
  accent-doux: '#DCEFE8'
  encre: '#1A1D22'
  encre-douce: '#51565F'
  gris: '#6E7278'
  trait: '#DADFE5'
  fond-creme: '#F6F4EF'
  attention: '#8A5A00'
  attention-doux: '#FBE9CF'
  danger: '#B3261E'
  danger-doux: '#F8DEDC'
focus:
  outline: '2px solid {colors.primaire}'
  offset: '2px'
typography:
  surtitre:
    fontFamily: "'Aptos', 'Segoe UI', system-ui, sans-serif"
    fontSize: 12px
    fontWeight: '600'
    lineHeight: '1.3'
    letterSpacing: 0.08em
  titre:
    fontFamily: "'Aptos', 'Segoe UI', system-ui, sans-serif"
    fontSize: 22px
    fontWeight: '600'
    lineHeight: '1.25'
  sous-titre:
    fontFamily: "'Aptos', 'Segoe UI', system-ui, sans-serif"
    fontSize: 16px
    fontWeight: '600'
    lineHeight: '1.3'
  corps:
    fontFamily: "'Aptos', 'Segoe UI', system-ui, sans-serif"
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
  petit:
    fontFamily: "'Aptos', 'Segoe UI', system-ui, sans-serif"
    fontSize: 12px
    fontWeight: '400'
    lineHeight: '1.4'
  chasse-fixe:
    fontFamily: "'Cascadia Mono', Consolas, monospace"
    fontSize: 13px
    fontWeight: '400'
    lineHeight: '1.5'
rounded:
  sm: 12px
  md: 16px
  lg: 22px
  full: 9999px
spacing:
  '1': 4px
  '2': 8px
  '3': 12px
  '4': 16px
  '5': 24px
  '6': 32px
  '7': 48px
  gutter: 24px
components:
  bandeau-demonstration:
    background: '{colors.primaire-fonce}'
    foreground: '#FFFFFF'
    fontSize: '{typography.petit.fontSize}'
  en-tete:
    background: '#FFFFFF'
    border-bottom: '{colors.trait}'
    height: 56px
    nom: '{typography.titre}'
    lot: '{typography.petit}'
  carte-depot:
    background: '{colors.fond-creme}'
    border: '{colors.trait}'
    border-style: dashed
    radius: '{rounded.md}'
  selecteur:
    radius: '{rounded.sm}'
    border: '{colors.trait}'
  barre-progression:
    track: '{colors.trait}'
    fill: '{colors.accent}'
    radius: '{rounded.full}'
  pastille-statut:
    radius: '{rounded.full}'
    ok:
      background: '{colors.accent-doux}'
      foreground: '{colors.accent}'
    a-revoir:
      background: '{colors.attention-doux}'
      foreground: '{colors.attention}'
    validee:
      background: '{colors.primaire-doux}'
      foreground: '{colors.primaire}'
    ecartee:
      background: '{colors.trait}'
      foreground: '{colors.encre-douce}'
    en-generation:
      background: '{colors.trait}'
      foreground: '{colors.encre-douce}'
  barre-candidats:
    tab-actif:
      border-bottom: '{colors.primaire}'
      foreground: '{colors.primaire}'
    tab-inactif:
      foreground: '{colors.encre-douce}'
  panneau-note:
    background: '{colors.fond-creme}'
    fontFamily: '{typography.chasse-fixe.fontFamily}'
  formulaire-fiche:
    radius: '{rounded.sm}'
    border: '{colors.trait}'
    focus-border: '{colors.primaire}'
  champ-cvss:
    fontFamily: '{typography.chasse-fixe.fontFamily}'
    score-radius: '{rounded.full}'
    severite-faible:
      background: '{colors.accent-doux}'
      foreground: '{colors.accent}'
    severite-moyenne:
      background: '{colors.attention-doux}'
      foreground: '{colors.attention}'
    severite-elevee:
      background: '{colors.danger-doux}'
      foreground: '{colors.danger}'
    severite-critique:
      background: '{colors.danger}'
      foreground: '#FFFFFF'
  encart-motifs:
    background: '{colors.attention-doux}'
    border: '{colors.attention}'
    radius: '{rounded.sm}'
  barre-actions:
    background: '#FFFFFF'
    border-top: '{colors.trait}'
  bouton-primaire:
    background: '{colors.primaire}'
    foreground: '#FFFFFF'
    radius: '{rounded.sm}'
  bouton-secondaire:
    background: 'transparent'
    foreground: '{colors.primaire}'
    border: '{colors.trait}'
    radius: '{rounded.sm}'
  indicateur-enregistrement:
    foreground: '{colors.encre-douce}'
  boite-confirmation:
    background: '#FFFFFF'
    radius: '{rounded.md}'
    overlay: 'rgba(26,29,34,0.4)'
  page-incident:
    background: '#FFFFFF'
    carte-detection-radius: '{rounded.md}'
---

## Brand & Style

WaveAudit est un outil de travail, pas une vitrine. Il sert à relire et corriger des constats
générés localement, sous contrainte de temps (une consultante rend son rapport le lendemain) et
de confiance (chaque fiche doit pouvoir être vérifiée face à sa note source). Le style est
**sobre et fonctionnel** : une seule teinte primaire, peu de décorum, de la densité maîtrisée.
Rien d'externe (pas de police téléchargée, pas de CDN) : l'outil tourne hors ligne sur
`127.0.0.1`. Pas d'animation vitrine (curseur personnalisé, compteurs animés, révélations au
défilement) — seules des transitions discrètes d'état (apparition d'une fiche, changement de
statut).

Ce fichier définit les **rôles** de tokens avec des valeurs neutres (bleu ardoise sobre). Une
surcharge de marque privée (`theme-prive/web/theme.css`) redéfinit les mêmes variables CSS avec
les valeurs réelles de l'entreprise ; `theme-prive/web/logo.svg` s'affiche dans l'en-tête s'il
est présent. Ce mécanisme et ces fichiers ne sont jamais commités : `theme-prive/` est ignoré
par git. Le dépôt public ne contient aucune valeur de charte.

## Colors

Douze rôles, tous utilisés avec un libellé ou une icône en plus de la couleur (jamais la couleur
seule, AD-14 / accessibilité).

- **`primaire`** (`#30507D`) — actions principales (Valider, Exporter), liens, candidat actif,
  focus. Contraste 8,2:1 sur blanc.
- **`primaire-fonce`** (`#1C2E47`) — bandeau de démonstration, survol des boutons primaires.
- **`primaire-doux`** (`#E3E9F0`) — fond des pastilles « validée », survol des lignes de liste.
  `primaire` sur `primaire-doux` : 6,7:1.
- **`accent`** (`#2F6657`) — unique accent secondaire, réservé au statut « générée (ok) », à la
  sévérité CVSS « faible » et à la barre de progression. Jamais décoratif. Contraste sur
  `accent-doux` : 5,6:1 ; sur blanc : 6,6:1.
- **`accent-doux`** (`#DCEFE8`) — fond de la pastille « ok » et de la pastille de sévérité CVSS
  « faible ».
- **`encre`** (`#1A1D22`) / **`encre-douce`** (`#51565F`) — texte principal / texte secondaire.
  `encre-douce` sur blanc : 7,4:1.
- **`gris`** (`#6E7278`) — texte désactivé, métadonnées (durée, taille de fichier, score des
  candidats). Contraste 4,8:1 sur blanc (seuil AA 4,5:1).
- **`trait`** (`#DADFE5`) — bordures, séparateurs, carte de dépôt.
- **`fond-creme`** (`#F6F4EF`) — fond de la carte de dépôt et du panneau note (lecture longue).
- **`attention`** (`#8A5A00`) — statut « à revoir », encart des motifs, sévérité CVSS « moyenne ».
  Contraste 5,9:1 sur blanc ; 5,0:1 sur `attention-doux`.
- **`attention-doux`** (`#FBE9CF`) — fond doux de l'attention : pastille « à revoir », encart des
  motifs, pastille de sévérité CVSS « moyenne ». Seul nom de token pour ce rôle (plus de hex en
  dur dans les composants).
- **`danger`** (`#B3261E`) — erreurs bloquantes (moteur injoignable, lot déjà en cours), sévérité
  CVSS « élevée » (texte sur `danger-doux`) et « critique » (fond plein, texte blanc). Contraste
  6,5:1 sur blanc ; 5,1:1 sur `danger-doux` ; blanc sur `danger` plein : 6,5:1.
- **`danger-doux`** (`#F8DEDC`) — fond doux du danger : pastille de sévérité CVSS « élevée ».

Pas de dégradé, pas de couleur de marque tierce. Deux couleurs porteuses de sens (primaire,
accent) et c'est tout ; `attention` et `danger` restent des signaux d'alerte, pas des accents
décoratifs.

### Sévérité CVSS → token couleur

La pastille de score CVSS reprend des tokens de couleur existants (jamais la couleur seule,
toujours avec le libellé de sévérité) :

| Sévérité CVSS | Token foreground | Token background |
|---|---|---|
| Faible (0.1–3.9) | `{colors.accent}` | `{colors.accent-doux}` |
| Moyenne (4.0–6.9) | `{colors.attention}` | `{colors.attention-doux}` |
| Élevée (7.0–8.9) | `{colors.danger}` | `{colors.danger-doux}` |
| Critique (9.0–10.0) | `#FFFFFF` | `{colors.danger}` (plein) |

Voir `components.champ-cvss.severite-*`. Cette table est distincte de celle des pastilles de
statut de fiche (ok/à-revoir/validée/écartée) : les deux évoluent indépendamment, aucun partage
implicite de couleur entre sévérité CVSS et statut de fiche au-delà du token réutilisé.

### Focus visible

Token `focus` : contour `2px solid {colors.primaire}`, décalage (`offset`) `2px`, sur tout élément
interactif au focus clavier (champs, boutons, onglets, lignes de tiroir). Remplace tout focus
reposant sur le seul changement de couleur de bordure.

## Typography

Aucune police téléchargée (hors ligne) : `'Aptos', 'Segoe UI', system-ui, sans-serif` pour le
texte, `'Cascadia Mono', Consolas, monospace` pour la chasse fixe (notes brutes, vecteur CVSS,
identifiants de détection). Échelle courte : `surtitre` (12px, capitales espacées, pour les
intitulés de section comme « RUBRIQUES » ou « CANDIDATS »), `titre` (22px, titre de page),
`sous-titre` (16px, titre de fiche ou de carte), `corps` (14px, texte courant et formulaires),
`petit` (12px, métadonnées, bandeau), `chasse-fixe` (13px).

## Layout & Spacing

Grille d'espacement en base 4 (4 à 48px). `gutter` (24px) cadre les colonnes de la relecture :
tiroir de liste (fixe, ~260px) — note en lecture seule — fiche éditable, sur une largeur utile de
1366 à 1920 px (AD : pas de mobile, pas de redimensionnement sous 1366). Le tiroir se replie
automatiquement sous 1440px de largeur utile (y compris à 200% de zoom navigateur, reflow WCAG
1.4.10) pour laisser la place à la relecture ; il reste manuellement repliable au-dessus de ce
seuil (voir EXPERIENCE.md.Component Patterns).

## Elevation & Depth

Pas de superposition d'ombres marquées : le produit est plat et dense. Une seule élévation
utile, pour les éléments flottants (boîte de confirmation, menu déroulant) : ombre diffuse légère
(`rgba(26,29,34,0.12)`, flou 12px) pour les distinguer du contenu sous-jacent, sans effet de
profondeur décoratif.

## Shapes

Rayons `sm` (12px, champs et boutons), `md` (16px, cartes et boîtes de dialogue), `lg` (22px,
carte de dépôt), `full` (pastilles de statut, barre de progression). Les angles adoucis
distinguent les zones interactives (champs, boutons) des zones de lecture (note, panneau de
fiche), qui restent carrées.

## Components

→ Illustration de référence : [`mockups/relecture.html`](mockups/relecture.html), écran de
relecture. Les spines (`DESIGN.md` / `EXPERIENCE.md`) priment sur la maquette en cas de conflit.

| Composant | Spécification visuelle |
|---|---|
| **Bandeau démonstration** | Bande pleine largeur, fond `{colors.primaire-fonce}`, texte blanc `{typography.petit}`, centré, non masquable, en haut et en bas de chaque page. |
| **En-tête** | Fond blanc, bordure basse `{colors.trait}`, hauteur 56px. Nom « WaveAudit » en `{typography.titre}` (22px) à gauche ; logo privé à sa gauche s'il existe (`theme-prive/web/logo.svg`), sinon rien à sa place. Bloc `.lot` à droite (nom du lot, nombre de notes, état) en `{typography.petit}`, couleur `{colors.encre-douce}`. |
| **Carte de dépôt** | Grande zone `{rounded.lg}`, fond `{colors.fond-creme}`, bordure en tirets `{colors.trait}` ; icône de dépôt, texte « Déposez vos notes ici ou cliquez pour choisir des fichiers », liste des fichiers choisis en dessous avec taille et bouton de retrait. |
| **Sélecteurs modèle et langue** | Deux listes déroulantes `{rounded.sm}`, bordure `{colors.trait}`, label au-dessus en `{typography.petit}`. Le sélecteur de modèle affiche nom, durée indicative par fiche et mémoire ; l'entrée désactivée (modèle absent) est grisée `{colors.gris}`. |
| **Barre de progression du lot** | Piste `{colors.trait}`, remplissage `{colors.accent}`, `{rounded.full}`, hauteur 8px ; compteur « 4 / 12 fiches » à droite. |
| **Journal d'événements** | Liste chronologique compacte sous la barre, `{typography.petit}`, une ligne par événement (fiche démarrée, terminée, non rattachée), icône de statut à gauche. |
| **Tiroir de la liste des fiches** | Colonne fixe ~260px, fond blanc, une ligne par fiche : nom de note tronqué, pastille de statut, actif au clic (fond `{colors.primaire-doux}`). Repliable via un bouton en tête de colonne. |
| **Pastille de statut** | `{rounded.full}`, icône + libellé (jamais la couleur seule) : générée/ok (`{components.pastille-statut.ok}`), à revoir (`{components.pastille-statut.a-revoir}`), validée (`{components.pastille-statut.validee}`), écartée et en génération (`{components.pastille-statut.ecartee}`, icône animée douce pour « en génération »). |
| **Barre des candidats** | Trois onglets au-dessus de la fiche, un par constat candidat, avec score en `{typography.petit}` chasse fixe ; onglet actif souligné `{colors.primaire}`. |
| **Panneau note** | Colonne de gauche en lecture seule, fond `{colors.fond-creme}`, texte en `{typography.chasse-fixe}` pour préserver la mise en forme d'origine de la note. |
| **Formulaire de fiche** | Colonne de droite : zones de texte `{rounded.sm}` bordure `{colors.trait}`, focus `{colors.primaire}`, pour titre / description / impact / recommandation. Liste de références en lecture, retrait seul. |
| **Champ CVSS** | Champ texte chasse fixe pour le vecteur, score et sévérité recalculés à côté en pastille `{rounded.full}` colorée selon la table « Sévérité CVSS → token couleur » ci-dessus (`{components.champ-cvss.severite-*}`, jamais la couleur seule). |
| **Encart des motifs** | Bloc `{rounded.sm}`, fond `{colors.attention-doux}`, bordure `{colors.attention}`, liste des motifs en langage clair sous l'icône d'avertissement, visible si la fiche est « à revoir » ; chaque motif porte la mention « signalé à la génération ». |
| **Barre d'actions** | Pleine largeur en bas de la relecture, fond blanc, bordure haute `{colors.trait}` : boutons Valider (primaire), Suivante (secondaire), Exporter et Exporter un brouillon (secondaire), alignés à droite. |
| **Indicateur d'enregistrement** | Petit texte discret `{colors.encre-douce}` près de la barre d'actions : « Enregistré » / « Enregistrement… », pas d'icône animée intrusive. |
| **Boîte de confirmation** | Boîte modale centrée, fond blanc, `{rounded.md}`, superposition `rgba(26,29,34,0.4)` : message court, deux boutons (annuler / confirmer en danger si destructeur). |
| **Page incident** | Résumé des détections en cartes `{rounded.md}` (titre, sévérité en pastille, nombre d'occurrences) ; liste des détections en tableau dense ; bouton de téléchargement du rapport en bouton primaire. |

## Do's and Don'ts

| Do | Don't |
|---|---|
| Une seule teinte primaire, un seul accent, sens fixe pour chacun | Ajouter une couleur de marque tierce ou un dégradé |
| Icône + libellé pour chaque statut | Coder un statut par la couleur seule |
| Polices système uniquement, tout en local | Charger une police ou une ressource depuis un CDN |
| Transitions discrètes d'état (apparition, changement de statut) | Animation vitrine : curseur personnalisé, compteurs, révélations au défilement, barre de progression de défilement |
| Chasse fixe pour la note brute et les identifiants techniques | Reformater la note brute (elle doit rester fidèle à la source) |
| Bandeau de démonstration visible en permanence | Permettre de masquer ou réduire le bandeau |
| Focus clavier = token `focus` (contour 2px + décalage 2px) sur tout élément interactif | Un focus qui ne change que la couleur de bordure |
| Respecter `prefers-reduced-motion` : supprimer les transitions d'état si demandé par le système | Forcer une transition ou une animation quand le système demande de les réduire |
