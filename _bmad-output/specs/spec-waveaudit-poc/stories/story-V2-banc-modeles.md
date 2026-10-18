---
id: story-V2
title: Banc des 4 modèles et réglage du prompt
status: review
sources:
  - ../stories.yaml
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
---

# Story V2 : banc des 4 modèles et réglage du prompt

## Livré

- `waveaudit banc` lancé sur 6 notes de démonstration pour les 4 modèles : 01, 11 et 16 (classiques), 22, 26 et 29 (difficiles).
  - Toutes les fiches sont ok, top1 4/6 et top3 6/6 pour chaque modèle.
  - Médiane par fiche de 11 à 20 s. Pic RSS total de 1,3 à 2,8 Gio.
- Relecture des 6 fiches du modèle par défaut : 0 utilisable tel quel, 4 retouches légères, 2 à refaire (les notes 01 et 29, mal rattachées).
- 3 itérations de réglage de la consigne sur granite. Mesures : taux ok, motifs, durée médiane et recopie du catalogue.
- Workflow incident mesuré sur la démo CERT avec le défaut et le repli : 16/16 récits ok pour chacun.
- Bilan, tableaux et recommandation pour l'EliteBook : `_bmad-output/implementation-artifacts/bilan-modeles.md`.

## Réglages retenus

Aucun. `prompt.py`, `temperature` et `max_tokens` restent inchangés.

- Les essais réduisent la recopie du catalogue (description : de 0,89 à 0,35-0,56).
- Mais ils allongent la durée médiane (de 17 s à 22-34 s) et n'augmentent pas le taux ok.
- Ils introduisent aussi des boucles de répétition et des erreurs de sens.
- La consigne de l'essai 3 est consignée dans le bilan, pour une reprise avec une pénalité de répétition ou avec qwen3-1.7b.

## Recommandation

Les rôles sont inchangés. qwen3-1.7b adapte nettement mieux les fiches. Il est recommandé comme défaut sur l'EliteBook, sous trois conditions :

- il tient en mémoire (environ 2,8 Gio) ;
- le garde-fou cesse de retirer l'URL de l'actif quand elle vient de la note ;
- le banc est refait sur l'EliteBook.

## Reports

- Rattachement des notes 01 (XSS réfléchi contre stocké) et 29 (SSTI contre divulgation d'erreurs) : recherche ou catalogue.
- Garde-fous fiches :
  - une sortie dégénérée par répétition reste `ok` ;
  - l'URL de l'actif citée depuis la note est retirée (`reference_retiree`) ;
  - le seuil de 20 caractères pénalise un titre court.
- `repeat_penalty` à exposer dans `[moteur]` et `moteur_openai`.
- Récit d'incident en anglais avec MiniCPM5 (1/16), avec le statut `ok`.

## Vérifications

- Un seul llama-server à la fois. Psutil ne trouvait aucun llama-server restant après chaque run.
- Chaque run a duré moins de 10 min. Aucun téléchargement.
- Garde réseau actif : les commandes `banc` et `incident` n'ont pas été modifiées.
- Aucun fichier de code modifié : la suite non slow et ruff restent verts.
