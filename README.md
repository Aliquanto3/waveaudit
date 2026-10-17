# WaveAudit

Assistant IA **hors ligne** pour les consultants en audit de cybersécurité, sur un PC professionnel de 16 Go sans GPU. Il rédige des **fiches de vulnérabilité** à partir des notes brutes du consultant, en retrouvant le constat type dans un catalogue puis en l'adaptant au contexte. Aucune donnée ne quitte le poste.

> **État : en spécification.** Ce dépôt contient pour l'instant le cadrage du POC. Le POC ne traite que des données publiques ou fictives.

## Pourquoi en local

Les données de mission d'un audit de sécurité (preuves, vulnérabilités, extractions) ne doivent pas sortir d'un périmètre maîtrisé : qualification PASSI, clauses contractuelles. Les assistants IA dans le cloud sont donc exclus pour ces tâches. Un petit modèle de langage (SLM) qui tourne sur le poste ne fait sortir aucune donnée.

## Principes du POC

- **Moteur interchangeable** : l'application parle à un endpoint compatible OpenAI. Elle utilise un SLM local aujourd'hui, et pourra se brancher sur un LLM interne cloisonné demain.
- **Adapter, pas inventer** : le modèle part d'un constat type du catalogue (CWE, OWASP WSTG, guides de l'ANSSI) et l'adapte aux notes. Il n'inclut aucune référence absente du catalogue.
- **Par lot, pas en chat** : sur CPU, une fiche est générée en arrière-plan pendant que le consultant continue de travailler.
- **Vérifiablement hors ligne** : un test automatisé vérifie l'absence d'appel sortant. Le dépôt fournit un SBOM, et les empreintes SHA-256 des poids, dont la source est documentée.
- **Installation simple et auditable** : on clone le dépôt, puis on lance `uv sync`.

## Critères de réussite du POC

| Axe | Seuil |
|---|---|
| Qualité | ≥ 70 % de fiches utilisables après retouches légères (20 notes fictives) |
| Fiabilité | 0 référence inventée |
| Vitesse | < 3 min par fiche sur un portable 16 Go, suite bureautique ouverte |
| Mémoire | Pic ≤ 6 Go |
| Installation | < 10 min |

## Contenu du dépôt

- `_bmad-output/forge/slm-edge-consultants-cyber/` : cadrage de l'idée (`forged-idea.md`) et rapport de la session (`forge-report.html`).
- `_bmad/`, `.claude/skills/` : méthode [BMAD](https://github.com/bmad-code-org/BMAD-METHOD) pour la spécification et le développement.
- `.claude/cost-kit/` : contrôle rapide de [agent-cost-kit](https://github.com/Aliquanto3/agent-cost-kit).

## Licence

[Apache 2.0](LICENSE).
