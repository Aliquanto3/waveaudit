# Revue — story 1.3 (renommage en pentest-scribe, charte générique)

Brief : `regles-debrand.md`, `charte-generique.md` et `brief-story-1x.md` du run (hors dépôt). Branche `chore/charte-generique`, à jour sur `origin/main`.

## Revue

### Passe 1 (2026-11-03, SHA revu ab4d542)

- Important, medium, second avis 1 : le repli `waveaudit.local.toml` émettait un `DeprecationWarning`, masqué hors `__main__`, que l'utilisateur de la CLI ne voyait jamais. Corrigé : `FutureWarning`, affiché par défaut (vérifié hors pytest : le message sort sur stderr), et tests de `test_config.py` alignés.
- Pre-existing, medium, second avis 2 : `ci.yml` ne tourne que sur push `main` et `workflow_dispatch`, et sur Windows seul. Reporté : l'orchestrateur lance la CI à la demande, workflow inchangé.
- Nit, low, second avis 3 : le pictogramme SVG de `base.html` n'avait pas de valeurs de repli. Corrigé : `#0B6B78`, `#B4500F` et `#FFFFFF` ajoutés, et le trait passe à `--couleur-sur-statut`.
- Nit, low, second avis 4 : le texte blanc sur aplat (`danger`, `primaire`) n'utilisait pas de jeton dédié. Corrigé : `--couleur-sur-statut: #FFFFFF` ajouté à `tokens.css` et à `DESIGN.md`, utilisé pour la pastille critique et le bouton primaire. `test_contraste` gagne les paires `sur-statut`/`danger` (6,6:1) et `sur-statut`/`primaire` (6,2:1).
- Nit, low, second avis 5 : `--couleur-texte-sur-vif` est inutilisé. Rejeté : le jeton figure dans `DESIGN.md` et la charte le réserve à `alerte`.
- Nit, low, second avis 6 : lien privé `claude.ai/artifact` et mentions « collègues ». Corrigé : lien retiré de `etat-v2.md` et de `recette-v2.md` (oubli du second avis). Les 17 mentions « collègues » de `_bmad-output` deviennent « testeurs » ou « auditeurs ». « EliteBook 16 Go » est gardé.
- Nit, low, second avis 7 : couleur Word `1F3864`. Rejeté : couleur neutre, hors charte web.
- Nit, low, reviewer : le chemin `C:\Users\anael.yahi\…` de `review-grille-rapprochement.md` révélait un compte de poste interne. Corrigé : chemin rendu relatif au dépôt.
- Nit, low, reviewer : il reste des références croisées `wavelocalai` et `WaveStack` dans `_bmad-output` (forge, mémos d'architecture et de spec). Reporté à la story 2.1 (références croisées).
- Complexité : 0 constat. Le diff ne fait grandir aucune structure pendant l'exécution.

Vérifications : `ruff check` et `ruff format --check` passent. `test_config`, `test_contraste`, `test_architecture`, `test_cli` (unitaires et e2e) et l'e2e `test_ui` donnent 149 tests réussis. Suite complète non lancée (run parallèle) : la CI de branche en tient lieu.
