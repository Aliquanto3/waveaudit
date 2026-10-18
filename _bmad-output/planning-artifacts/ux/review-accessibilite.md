# Relecture accessibilité — spines UX WaveAudit v2

Sources : DESIGN.md, EXPERIENCE.md, mockups/relecture.html. Cible WCAG 2.1 AA, clavier + NVDA/Narrateur.

## Haute

1. Labels de formulaire non associés aux champs (label et input frères, sans `for`/`id`) — mockup `.champ` Titre/Description/Impact/Recommandation/CVSS (relecture.html l.321-347). Corriger : `for=`/`id=` ou envelopper l'input dans le `<label>`.
2. Barre des candidats sans sémantique ARIA (de simples `<button>`, pas de `role="tablist/tab"`, `aria-selected`, navigation flèches) — `.barre-candidats` (l.290-294), EXPERIENCE « Barre des candidats ». Corriger : patron APG Tabs complet.
3. Lignes du tiroir non accessibles au clavier (`div` cliquable sans `role`/`tabindex`) — `.ligne-fiche` (l.266-285). Corriger : `<button>` ou `role="listbox"`/`option"` avec gestion clavier.
4. Contraste insuffisant du gris `#80868F` sur blanc (~3,7:1, sous 4,5:1) — score des candidats (`.score`), métadonnées DESIGN.md. Corriger : foncer `gris` ou le réserver au seul état désactivé.
5. Contraste pastille « ok » (`accent` #3D7A68 sur `accent-doux` #DCEFE8) ≈4,2:1 pour un texte 11-12px, sous le seuil AA — DESIGN.md `pastille-statut.ok`. Corriger : foncer `accent` ou assombrir légèrement `accent-doux`.
6. Repli du tiroir à 1366 px / zoom 200 % décrit dans EXPERIENCE mais aucune media query dans le mockup — risque d'échec WCAG 1.4.10 (reflow). Corriger : ajouter le point de rupture CSS manquant.
7. Focus clavier reposant sur le seul changement de `border-color` (1px, `outline:none`) — `.champ textarea:focus/input:focus`. Corriger : ajouter un contour visible supplémentaire (box-shadow/outline épais).

## Moyenne

8. `aria-live="polite"` prévu sur tout le journal d'événements : risque de verbosité (une annonce par ligne) — EXPERIENCE Accessibility Floor. Corriger : n'annoncer qu'un résumé agrégé, garder le détail visuel seul.
9. Pas d'`aria-busy`/annonce précisée pendant la régénération d'un candidat (« Génération en cours ») — EXPERIENCE Barre des candidats. Corriger : `aria-busy="true"` sur `.panneau-fiche` + annonce ponctuelle de fin.
10. Bouton « Valider » désactivé explique la raison par info-bulle (`title`), peu fiable au clavier/lecteur d'écran — EXPERIENCE Barre d'actions. Corriger : `aria-describedby` vers un texte visible.
11. Erreur du vecteur CVSS non liée au champ (pas d'`aria-describedby`/`aria-invalid` spécifié) — EXPERIENCE Champ CVSS, `.champ.cvss`. Corriger : lier l'erreur et poser `aria-invalid="true"`.
12. `Alt+↑`/`Alt+↓` risquent un conflit avec le comportement natif Windows d'ouverture de liste déroulante quand le focus est sur un `<select>` — EXPERIENCE Interaction Primitives. Corriger : ignorer ces raccourcis si le focus est dans un champ de formulaire.
13. Boîte de confirmation : focus initial et retour du focus au déclencheur non spécifiés (seul `Échap` l'est) — EXPERIENCE Component Patterns. Corriger : documenter focus initial (bouton annuler) et retour à la fermeture.

## Basse

14. Mockup ne démontre pas le `lang` distinct du contenu de fiche (fr/en) exigé par EXPERIENCE — ajouter `lang=` sur `.panneau-note`/`.panneau-fiche`.
15. Aucune règle `prefers-reduced-motion` dans le mockup (non bloquant, aucune animation actuelle) — à poser avant d'implémenter les transitions d'état.
