# Validation Report — WaveAudit UX v2

- **DESIGN.md:** `_bmad-output/planning-artifacts/ux/DESIGN.md`
- **EXPERIENCE.md:** `_bmad-output/planning-artifacts/ux/EXPERIENCE.md`
- **Run at:** 2026-10-18

## Overall verdict

Deux relectures externes (grille de cohérence des spines, accessibilité WCAG 2.1 AA) ont été
intégrées dans `DESIGN.md`, `EXPERIENCE.md` et `mockups/relecture.html`. Tous les constats haute
et moyenne des deux relectures sont corrigés, ainsi que les trois constats basses de la relecture
grille et les deux de la relecture accessibilité (corrections tenant en une ligne). Les spines
passent en `status: final`.

Le point le plus structurant était l'absence de table explicite sévérité CVSS → couleur : elle
est posée dans `DESIGN.md` (faible → accent, moyenne → attention, élevée → danger sur fond doux,
critique → danger plein), avec un token `danger-doux` nouveau pour couvrir le cas « élevée ».
Côté accessibilité, deux tokens de couleur ont été recalculés (`gris`, `accent`) pour atteindre
4,5:1 AA, et le focus clavier repose désormais sur un token dédié (contour 2px + décalage 2px)
plutôt que sur le seul changement de couleur de bordure.

## Category verdicts (relecture grille)

- Flux — corrigé (étape et chemin alternatif brouillon ajoutés au Flow 1)
- Tokens — corrigé (`attention-doux` remplace le hex en dur)
- Composants — corrigé (lignes Component Patterns bandeau/en-tête ajoutées)
- États — corrigé (lignes State Patterns Lots récents + Suivi incident ajoutées)
- Références visuelles — corrigé (lien DESIGN.md → maquette ajouté)
- Bloat / Héritage / Forme — déjà strong, aucune action

## Findings — relecture grille (9/9 corrigés)

### Haute (2)
1. **Taille du nom d'en-tête** (mockup l.63 vs DESIGN.md Components l.224) — *Corrigé* :
   `.en-tete .nom` passe à 22px dans la maquette, aligné sur `{typography.titre}`.
2. **Mapping sévérité CVSS ↔ couleur ambigu** (DESIGN.md, Champ CVSS) — *Corrigé* : table
   explicite ajoutée dans DESIGN.md (`components.champ-cvss.severite-*`).

### Moyenne (4)
3. **Bandeau/En-tête sans Component Patterns** — *Corrigé* : deux lignes ajoutées à
   EXPERIENCE.md.Component Patterns.
4. **« Exporter un brouillon » hors Key Flow** — *Corrigé* : chemin alternatif ajouté à la fin du
   Flow 1 (Camille, 17h, 9/12 fiches validées).
5. **State Patterns manquants (Suivi incident, Lots récents)** — *Corrigé* : lignes ajoutées pour
   les deux surfaces (en cours/terminé/échoué, vide/liste).
6. **Token non nommé `#FBE9CF`** — *Corrigé* : token `attention-doux` créé, remplace le hex dans
   `pastille-statut.a-revoir` et `encart-motifs`.

### Basse (3)
7. **Bloc `.lot` orphelin** — *Corrigé* : spécifié dans DESIGN.md.Components (En-tête) et
   EXPERIENCE.md.Component Patterns (En-tête).
8. **DESIGN.md sans lien vers la maquette** — *Corrigé* : lien relatif ajouté sous le titre
   Components, avec la mention « les spines priment ».
9. **Repassage automatique de l'encart des motifs (question ouverte)** — *Corrigé* : tranché —
   les motifs restent affichés, marqués « signalé à la génération », disparaissent à la
   validation. Retiré des Questions ouvertes.

## Findings — relecture accessibilité (15/15 corrigés)

### Haute (7)
1. **Labels non associés (for/id)** — *Corrigé* : `for=`/`id=` ajoutés sur tous les champs de la
   maquette.
2. **Barre des candidats sans ARIA Tabs** — *Corrigé* : `role="tablist"`/`tab`/`tabpanel`,
   `aria-selected`, `aria-controls` ; navigation flèches spécifiée dans EXPERIENCE.md.
3. **Lignes du tiroir non accessibles au clavier** — *Corrigé* : `role="listbox"`/`option`,
   `tabindex`, `aria-selected`, navigation clavier spécifiée.
4. **Contraste gris `#80868F` insuffisant (~3,7:1)** — *Corrigé* : `gris` → `#6E7278`, **4,8:1**
   sur blanc.
5. **Contraste pastille « ok » insuffisant (~4,2:1)** — *Corrigé* : `accent` → `#2F6657`, **5,6:1**
   sur `accent-doux`.
6. **Repli du tiroir / reflow 200% sans media query** — *Corrigé* : `@media (max-width: 1440px)`
   ajoutée à la maquette ; breakpoint documenté dans DESIGN.md.Layout & Spacing.
7. **Focus clavier = seul changement de bordure** — *Corrigé* : token `focus` (contour 2px +
   décalage 2px), règle `:focus-visible` globale dans la maquette.

### Moyenne (6)
8. **`aria-live="polite"` trop verbeux** — *Corrigé* : EXPERIENCE.md précise un résumé agrégé par
   palier, pas une annonce par ligne.
9. **Pas d'`aria-busy` pendant la régénération** — *Corrigé* : `aria-busy="true"` sur le panneau
   de fiche + annonce de fin, spécifié et posé dans la maquette (`aria-busy="false"` à l'état
   repos).
10. **Raison du bouton Valider désactivé en `title` seul** — *Corrigé* : `aria-describedby` vers
    un texte visible (`#raison-validation`).
11. **Erreur CVSS non liée au champ** — *Corrigé* : `aria-invalid`/`aria-describedby` posés dans
    la maquette et spécifiés dans EXPERIENCE.md.
12. **Conflit `Alt+↑`/`Alt+↓` avec les listes déroulantes Windows** — *Corrigé* : raccourcis
    remplacés par `Ctrl+Alt+↑`/`Ctrl+Alt+↓` (+ boutons), inactifs dans un champ de formulaire.
13. **Boîte de confirmation : focus initial et retour du focus non spécifiés** — *Corrigé* :
    focus initial sur « annuler », retour au déclencheur à la fermeture, documenté dans
    EXPERIENCE.md.

### Basse (2)
14. **`lang` absent sur le contenu de fiche** — *Corrigé* : `lang="fr"` posé sur `.panneau-note`
    et `.panneau-fiche` dans la maquette.
15. **Pas de règle `prefers-reduced-motion`** — *Corrigé* : règle ajoutée à la maquette.

## Nouveaux ratios de contraste (recalculés, inscrits dans DESIGN.md)

| Paire | Ancien ratio | Nouveau ratio |
|---|---|---|
| `gris` sur blanc | ~3,7:1 | **4,8:1** |
| `accent` sur `accent-doux` | ~4,2:1 | **5,6:1** |
| `attention` sur `attention-doux` | 5,0:1 (déjà conforme) | 5,0:1 (inchangé) |
| `danger` sur `danger-doux` (nouveau) | — | 5,1:1 |
| `danger` plein, texte blanc (critique) | — | 6,5:1 |

## Reviewer files
- `review-grille.md`
- `review-accessibilite.md`
