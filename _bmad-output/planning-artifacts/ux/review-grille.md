# Relecture grille — UX WaveAudit v2 (2026-10-18)

Spines : `DESIGN.md` / `EXPERIENCE.md`. Sources (`.memlog.md`, `arbitrages.md`, `contrats.md`, `formats-incident.md`) résolvent toutes. Aucune ressource externe, aucune valeur de charte Wavestone dans le dépôt public — conforme.

## Constats

1. **[haute]** Contradiction mockup/DESIGN : `.en-tete .nom` en 18px dans `mockups/relecture.html` (ligne 63) alors que DESIGN.md impose `{typography.titre}` = 22px pour ce même libellé (Components, ligne 224). *Correction :* aligner la maquette sur le token ou documenter une exception.
2. **[haute]** Ambiguïté de mapping couleur : DESIGN.md (Champ CVSS, ligne 234) dit colorer le score CVSS « selon la sévérité (mêmes couleurs que les pastilles de statut) », mais les sévérités CVSS (faible/moyenne/élevée/critique) n'ont pas de correspondance définie avec les 4 couleurs de statut (ok/à revoir/validée/écartée) — la maquette retombe arbitrairement sur la couleur « attention » pour « Moyenne ». *Correction :* table explicite sévérité → token couleur dans DESIGN.md.
3. **[moyenne]** Couverture composants incomplète : « Bandeau démonstration » et « En-tête » ont une ligne DESIGN.md.Components mais aucune ligne EXPERIENCE.md.Component Patterns (comportement : non masquable, contenu du bloc `.lot`). *Correction :* ajouter ces deux lignes au tableau Component Patterns.
4. **[moyenne]** Couverture des parcours : « Exporter un brouillon » n'est exercé par aucun Key Flow (seulement une phrase dans Component Patterns, ligne 83) ; le besoin « export final et brouillon » du périmètre n'a donc qu'un demi-parcours. *Correction :* ajouter une étape ou un sous-flux brouillon dans Flow 1.
5. **[moyenne]** Couverture des états : pas de State Patterns pour la surface « Suivi d'un lot (incident) » (en cours/terminé/échoué), ni pour « Lots récents » (vide/liste) — seules les variantes du workflow fiches sont couvertes. *Correction :* ajouter les lignes correspondantes ou noter explicitement l'héritage depuis « Suivi d'un lot ».
6. **[moyenne]** Token non nommé : `#FBE9CF` est répété en dur (pastille « à-revoir », encart-motifs) sans entrée dans `colors`, alors que le même rôle (fond doux de l'attention) suit ailleurs le motif `*-doux` (`accent-doux`, `primaire-doux`). *Correction :* créer `attention-doux` dans `colors` et remplacer les deux occurrences.
7. **[basse]** Le bloc `.lot` affiché dans l'en-tête de la maquette (nom du lot, nombre de notes, état) n'a pas de spécification dans DESIGN.md.En-tête — référence orpheline côté maquette.
8. **[basse]** DESIGN.md ne renvoie jamais vers `mockups/relecture.html` (seule EXPERIENCE.md le fait) ; lien absent côté visuel alors que les composants de la relecture y sont illustrés.
9. **[basse]** « Repassage automatique de l'encart des motifs » reste en question ouverte (EXPERIENCE.md l.205) : état transitoire non couvert par State Patterns, cohérent avec l'aveu mais à trancher avant story de dev.

## Verdict par catégorie

Flux : adequate (gap brouillon) · Tokens : adequate (gap #FBE9CF) · Composants : adequate (bandeau/en-tête) · États : thin (incident/lots récents) · Références visuelles : strong · Bloat : strong · Héritage : strong · Forme : strong.
