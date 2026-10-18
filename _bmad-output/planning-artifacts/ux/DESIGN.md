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
  # Charte Wavestone officielle (voir .memlog.md, override 2026-10-18) : valeurs inchangées.
  primaire: '#451DC7'
  primaire-fonce: '#250F6B'
  primaire-doux: '#EDE7FE'
  accent: '#04F06A'
  accent-doux: '#CAFEE0'
  encre: '#0A0A14'
  encre-douce: '#4A4A5E'
  gris: '#8A8A9E'
  trait: '#E6E6EC'
  fond-creme: '#F6F5FA'
  attention: '#FFCA4A'
  danger: '#FF2A49'
  # Rôles dérivés (accessibilité) : la valeur de marque sert au trait/fond plein, jamais en
  # petit texte porteur de sens. Calculs dans Colors > Rôles dérivés.
  accent-texte: '#036B38'
  gris-texte: '#616670'
  attention-doux: '#FBE9CF'
  attention-texte: '#8A5A00'
  danger-doux: '#F8DEDC'
  danger-texte: '#B3261E'
  texte-sur-vif: '#0A0A14'
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
      foreground: '{colors.accent-texte}'
    a-revoir:
      background: '{colors.attention-doux}'
      foreground: '{colors.attention-texte}'
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
      foreground: '{colors.accent-texte}'
    severite-moyenne:
      background: '{colors.attention-doux}'
      foreground: '{colors.attention-texte}'
    severite-elevee:
      background: '{colors.danger-doux}'
      foreground: '{colors.danger-texte}'
    severite-critique:
      background: '{colors.danger}'
      foreground: '{colors.texte-sur-vif}'
  encart-motifs:
    background: '{colors.attention-doux}'
    border: '{colors.attention}'
    foreground: '{colors.attention-texte}'
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

Ce fichier porte la **palette officielle Wavestone** (override Anaël, 2026-10-18 : le thème neutre
est refusé — voir `.memlog.md`). Seul le logo reste privé : le serveur sert
`theme-prive/web/logo.svg` dans l'en-tête quand ce fichier est présent sur le disque (test
d'existence côté Jinja, pas de valeur en dur dans le HTML), et n'affiche rien à sa place sinon ;
`theme-prive/` reste ignoré par git. `theme-prive/web/theme.css` n'existe plus : la palette
n'a plus besoin d'être surchargée, elle est publique.

## Colors

Palette officielle Wavestone (override Anaël, 2026-10-18), déclinée comme dans
`agentic-harness-training-demo` (`tokens.css` / son `DESIGN.md`, section Colors) : les valeurs de
marque restent telles quelles pour les traits, fonds pleins et grandes surfaces ; là où une paire
texte/fond tombe sous 4,5:1 AA, un **rôle dérivé** (`*-texte`) porte le même sens avec un ton plus
soutenu, toujours doublé d'une icône et d'un libellé (jamais la couleur seule, AD-14).

- **`primaire`** (`#451DC7`) — actions principales (Valider, Exporter), liens, candidat actif,
  focus. Contraste 9,3:1 sur blanc ; 7,7:1 sur `primaire-doux`.
- **`primaire-fonce`** (`#250F6B`) — bandeau de démonstration (texte blanc, 15,4:1), survol des
  boutons primaires.
- **`primaire-doux`** (`#EDE7FE`) — fond des pastilles « validée », survol des lignes de liste.
- **`accent`** (`#04F06A`) — vert de marque : barre de progression, trait et fond plein de la
  pastille de sévérité CVSS « critique ». Contraste 1,5:1 sur blanc : **jamais en texte**, jamais
  en trait fin isolé.
- **`accent-doux`** (`#CAFEE0`) — fond de la pastille « générée (ok) » et de la pastille de
  sévérité CVSS « faible ».
- **`accent-texte`** (`#036B38`, dérivé) — rôle de texte du vert : foreground du statut « générée
  (ok) » et de la sévérité CVSS « faible ». Contraste 6,6:1 sur blanc ; 5,9:1 sur `accent-doux`.
- **`encre`** (`#0A0A14`) / **`encre-douce`** (`#4A4A5E`) — texte principal / texte secondaire.
  `encre` sur blanc : 19,7:1 ; `encre-douce` sur blanc : 8,6:1. `encre` sert aussi de
  **`texte-sur-vif`** : foreground sur tout fond plein vif (vert, jaune, rouge) — 12,8:1 sur
  `accent`, 12,9:1 sur `attention`, 5,3:1 sur `danger`.
- **`gris`** (`#8A8A9E`) — bordures fines, icônes décoratives, puces non porteuses de sens.
  Contraste 3,4:1 sur blanc : **jamais en texte**.
- **`gris-texte`** (`#616670`, dérivé) — rôle de texte du gris : désactivé, métadonnées (durée,
  taille de fichier, score des candidats). Contraste 5,8:1 sur blanc ; 5,3:1 sur `fond-creme`.
- **`trait`** (`#E6E6EC`) — bordures, séparateurs, carte de dépôt.
- **`fond-creme`** (`#F6F5FA`) — fond de la carte de dépôt et du panneau note (lecture longue).
- **`attention`** (`#FFCA4A`) — jaune de marque : fond plein et trait de l'encart des motifs, de
  la pastille « à revoir », rôle « moyenne » en vecteur de fond. Contraste 1,5:1 sur blanc :
  **jamais en texte**.
- **`attention-doux`** (`#FBE9CF`, dérivé) — fond doux de l'attention : pastille « à revoir »,
  encart des motifs, pastille de sévérité CVSS « moyenne ».
- **`attention-texte`** (`#8A5A00`, dérivé) — rôle de texte de l'attention : foreground du statut
  « à revoir », de l'encart des motifs, de la sévérité CVSS « moyenne ». Contraste 5,9:1 sur
  blanc ; 5,0:1 sur `attention-doux`.
- **`danger`** (`#FF2A49`) — rouge de marque : erreurs bloquantes (moteur injoignable, lot déjà en
  cours), trait et fond plein de la sévérité CVSS « critique » (texte `texte-sur-vif`, 5,3:1).
  Contraste 3,7:1 sur blanc : **jamais en texte seul**.
- **`danger-doux`** (`#F8DEDC`, dérivé) — fond doux du danger : pastille de sévérité CVSS
  « élevée ».
- **`danger-texte`** (`#B3261E`, dérivé) — rôle de texte du danger : messages d'erreur, foreground
  de la sévérité CVSS « élevée ». Contraste 6,5:1 sur blanc ; 5,1:1 sur `danger-doux`.

Pas de dégradé, pas de couleur de marque tierce ajoutée. `primaire` et `accent` restent les deux
couleurs porteuses de sens côté marque ; `attention` et `danger` des signaux d'alerte, jamais des
accents décoratifs ; leurs rôles `*-texte` ne sont qu'une correction de contraste, pas une
nouvelle couleur de marque.

### Rôles dérivés (accessibilité)

| Rôle dérivé | D'après | Usage | Ratio AA (seuil 4,5:1) |
|---|---|---|---|
| `accent-texte` (`#036B38`) | `accent` (`#04F06A`, 1,5:1 sur blanc) | texte « générée (ok) », sévérité CVSS faible | 6,6:1 sur blanc, 5,9:1 sur `accent-doux` |
| `gris-texte` (`#616670`) | `gris` (`#8A8A9E`, 3,4:1 sur blanc) | métadonnées, texte désactivé | 5,8:1 sur blanc, 5,3:1 sur `fond-creme` |
| `attention-texte` (`#8A5A00`) | `attention` (`#FFCA4A`, 1,5:1 sur blanc) | texte « à revoir », sévérité CVSS moyenne | 5,9:1 sur blanc, 5,0:1 sur `attention-doux` |
| `danger-texte` (`#B3261E`) | `danger` (`#FF2A49`, 3,7:1 sur blanc) | messages d'erreur, sévérité CVSS élevée | 6,5:1 sur blanc, 5,1:1 sur `danger-doux` |
| `texte-sur-vif` (`#0A0A14` = `encre`) | texte sur tout fond plein vif | sévérité CVSS critique (fond `danger` plein) | 5,3:1 (le plus bas des trois fonds vifs) |

### Sévérité CVSS → token couleur

La pastille de score CVSS reprend des tokens de couleur existants (jamais la couleur seule,
toujours avec le libellé de sévérité) :

| Sévérité CVSS | Token foreground | Token background |
|---|---|---|
| Faible (0.1–3.9) | `{colors.accent-texte}` | `{colors.accent-doux}` |
| Moyenne (4.0–6.9) | `{colors.attention-texte}` | `{colors.attention-doux}` |
| Élevée (7.0–8.9) | `{colors.danger-texte}` | `{colors.danger-doux}` |
| Critique (9.0–10.0) | `{colors.texte-sur-vif}` | `{colors.danger}` (plein) |

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

→ Illustration de référence : [`mockups/prototype.html`](mockups/prototype.html), prototype
interactif couvrant tous les parcours. Les spines (`DESIGN.md` / `EXPERIENCE.md`) priment sur le
prototype en cas de conflit.

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
| **Encart des motifs** | Bloc `{rounded.sm}`, fond `{colors.attention-doux}`, bordure `{colors.attention}`, texte `{colors.attention-texte}`, liste des motifs en langage clair sous l'icône d'avertissement, visible si la fiche est « à revoir » ; chaque motif porte la mention « signalé à la génération ». |
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
