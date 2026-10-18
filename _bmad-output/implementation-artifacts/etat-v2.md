# État v2

Plan : `plan-v2.md`. États possibles : `à faire`, `en cours`, `intégrée <sha>`, `bloquée : raison`.

| Vague | Story | Titre | dev-story | État |
|---|---|---|---|---|
| 0 | S0 | Socle v2 | Opus | intégrée e0fa92b |
| 1 | Q1 | Nouvelle tentative seed + 1, balises neutralisées, repeat_penalty transmis | Sonnet | intégrée c63b766 |
| 1 | Q2 | Garde-fous v2 (seuils, URL de la note, répétition, langue) | Sonnet | intégrée ab6ea6d |
| 1 | R1 | Règles pures de relecture | Sonnet | intégrée 3ea74d7 |
| 1 | M1 | Verrou unique et moteur à la demande | Opus | intégrée 17e4353 |
| 1 | X1 | Rendu Word bilingue, modes final et brouillon | Sonnet | intégrée f976867 |
| 1 | W1 | Socle web (routeurs, CSRF, en-têtes, erreurs codées) | Opus | intégrée 6bb935f |
| 2 | Q3 | Catalogue bilingue et traduction des 50 constats ★ | Sonnet | en cours |
| 2 | W5 | Thème public et logo privé | Sonnet | en cours |
| 3 | Q4 | Index BM25 bilingue, rattachement des notes 01 et 29 | Sonnet | à faire |
| 3 | L1 | Langue du lot, de la CLI au Word | Sonnet | à faire |
| 4 | B1 | Banc v2 | Sonnet | à faire |
| 4 | R2 | Persistance de la relecture et lot.json | Opus | à faire |
| 5 | Q5 | Rebanc EliteBook, consigne et rôles ★ | Opus | à faire |
| 5 | W2 | Accueil, lots récents, suivi lu sur le disque | Sonnet | à faire |
| 6 | X2 | Service d'export et `waveaudit exporter` | Sonnet | à faire |
| 6 | W4 | Incident dans l'UI | Sonnet | à faire |
| 7 | W3a | API de relecture, régénération et export | Opus | à faire |
| 8 | W3b | Écran de relecture | Sonnet | à faire |
| 8 | DOC | README et guide des testeurs | Sonnet | à faire |
| 8 | REC | Recette finale sur l'EliteBook ★ | avec Anaël | à faire |

★ : point d'arrêt humain (voir `plan-v2.md`).

## Mode d'exécution (décidé avec Anaël le 2026-10-18)

- **Ordonnancement par dépendances** plutôt que par vagues : une story part dès que ses dépendances (en-tête de `stories.yaml`) sont intégrées. Q3 part dès Q2, W5 dès W1, L1 sans attendre Q4, B1 et R2 dès L1, DOC en parallèle de W3b. Intégration toujours une à une, dans l'ordre des collisions de fichiers partagés. Suite complète après S0, puis toutes les 3 ou 4 intégrations et en fin d'exécution.
- **Push** de `main` autorisé après chaque story revue, intégrée et verte.
- **Moins de sollicitations** : la relecture des 10 constats de Q3 est asynchrone (liste ci-dessous, corrections à tout moment avant Q5). Après le rebanc Q5, le modèle par défaut est choisi par la règle mécanique de CAP-7 et consigné avec ses chiffres ; Anaël peut l'infirmer. Les écarts au contrat et les stories bloquées sont consignés ici sans arrêter l'exécution. Restent avec Anaël : REC, puis le tag et la release 0.2.0.
- **Coupure de session** (après la vague 4, puis avant REC) : l'orchestrateur s'arrête et propose `/clear` à Anaël ; sans réponse sous 30 min, il continue.

## Relecture de Q3 (10 constats tirés au hasard)

À remplir à l'intégration de Q3.

## Écarts à arbitrer

- README : MiniCPM5 encore présenté comme repli (à réaligner par DOC). Repli qwen3.5-0.8b non essayé sur le vrai moteur (à vérifier en REC).
- X1 : dans un Word `en`, les `detail` des motifs (textes du domaine) et les codes bruts (`non_traitee`, `non_rattachee`, `vecteur_invalide`…) restent en français ; §23 ne compte pas les motifs parmi les effets de la langue. Accepter, ou prévoir une story de `detail` par langue.
- R1 : §25 dit que `modifier` fait `version + 1` sans exception, mais une correction identique ne doit rien changer. Consigne pour R2 : `modifier` n'écrit ni n'incrémente quand `operation(entree) == entree`.
- R1 : `cvss31.evaluer` (imposé par le contrat) accepte `CVSS:3.0/…` et les métriques temporelles.
- M1 : l'ouverture du moteur tient le verrou interne, donc `fermer()` attend une ouverture en cours ; à confronter à l'attente de 10 s du lifespan (E3) en W2. `utiliser("B")` pendant un usage sur « A » n'est pas gardé : la sérialisation repose sur VerrouUnique (W2).
- W1 : cinq codes d'erreur hors table §26 (`introuvable`, `methode_refusee`, `requete_invalide`, `erreur_http`, `erreur_interne`) ; `Cache-Control: no-store` partout sauf `/static/` ; 409 `lot_en_cours` sans `occupation` jusqu'à W2.
- Q2 : la comparaison de boucle à la source ignore la casse (contrat : « telle quelle ») ; côté incident, la source des étapes 5 et 6 inclut aussi les identifiants, IP et hachages reconnus légitimes ; `finditer` à la place de `re.search` pour ne pas masquer une boucle derrière une suite sans lettre.

## Bilan

À remplir en fin d'exécution.
