# WaveAudit — assistant d'audit cyber hors ligne

Windows, Python 3.12 géré par `uv` (pas de `python` global : `uv run …`).
Cadrage : `_bmad-output/forge/slm-edge-consultants-cyber/forged-idea.md` (décisions verrouillées, ne pas les rouvrir sans le dire).

## Règles du POC
- Aucun appel réseau sortant à l'exécution ; données publiques ou fictives seulement.
- Pas de charte ni de logo Wavestone dans le dépôt public : ils vont dans `theme-prive/` (ignoré par git).

## Commandes (à confirmer à l'architecture)
- Tests ciblés pendant le travail : `uv run pytest -q --tb=short <chemins>`
- Suite complète, une fois avant intégration : `uv run pytest -q --tb=line -p no:warnings`
- Lint et format : `uv run ruff check` et `uv run ruff format --check`
- Contrôle rapide (~5 s) : `uv run --no-sync python .claude/cost-kit/controle_rapide.py`

## Enchaînement par story (appels bloquants, une passe de revue)
1. `agent-cost-kit:dev-story` implémente et commite dans un worktree, sans fusionner.
2. `agent-cost-kit:second-avis` (Haiku, lecture seule) relit le diff.
3. `agent-cost-kit:reviewer` relit avec la liste du second avis, corrige et consigne.
4. La session principale intègre.
Recherches et lecture de logs : agent `agent-cost-kit:lookup`.
