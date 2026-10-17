# État de nuit

| Story | Titre | État |
|---|---|---|
| 1 | Socle commun | intégrée 080d53e (revue : revues/story-1.md, validée par Anaël) |
| 2 | Recherche BM25 | intégrée b74abe1 (revue : revues/story-2.md) |
| 3 | CVSS 3.1 et garde-fous | intégrée c980c3f (revue : revues/story-3.md) |
| 4 | Catalogue de constats types | en cours |
| 5 | Notes brutes et jeu de démonstration | à faire |
| 6 | Adaptateur moteur OpenAI | à faire |
| 7 | Garde réseau | à faire |
| 8 | Installation vérifiée et SBOM | à faire |
| 9 | Export Word et thèmes | à faire |
| 10 | Pipeline fiches et prompt | à faire |
| 11 | Calibrage du rattachement | à faire |
| 12 | Composition, lot, llama-server | à faire |
| 13 | CLI complète | à faire |
| 14 | UI web locale | à faire |
| 15 | Banc de mesure | à faire |
| 16 | Preuve hors ligne, test réel, README | à faire |
| V1 | Validation sur le vrai moteur | à faire |
| V2 | Banc des 4 modèles et réglage du prompt | à faire |
| D1 | Catalogue élargi et notes difficiles | à faire |
| D2 | Intégration continue GitHub Actions | à faire |
| D3 | Guide des testeurs et formulaire de retour | à faire |
| C1 | Extension du socle pour le CERT | à faire |
| C2 | Lecture des journaux et jeu de démo | à faire |
| C3 | Règles et moteur de détection | à faire |
| C4 | Indicateurs et garde-fous du récit | à faire |
| C5 | Workflow incident, service, calibrage | à faire |
| C6a | Rapport d'incident Word | à faire |
| C6b | CLI incident, hors ligne, README | à faire |

## Écarts à arbitrer

- Story 2 : la tokenisation remplace œ, æ, ß (oe, ae, ss) avant NFKD ; le §7 ne cite que NFKD (sans cela « œuvre » donne « uvre »). Écart mineur, à entériner dans contrats.md.
- Story 3 (reporté par la revue) : conformément au §6, un titre de moins de 20 caractères (ex. « Injection SQL ») est remplacé par celui du constat type et la fiche passe `a_revoir` ; seuil probablement trop strict, à vérifier au banc.
