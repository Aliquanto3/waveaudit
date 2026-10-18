# Mesures de qualité v2 (CAP-5 à CAP-7)

Le protocole reprend celui de `bilan-modeles.md`. Les résultats y sont consignés.

## Poste et protocole

- Poste : l'EliteBook cible (i5-1145G7, 4 cœurs physiques, 15,7 Gio, Windows 11), llama-server en CPU, `threads = 4`, `ctx = 4096`.
- Commande : `uv run waveaudit banc var/banc-sous-ensemble --modele <nom>`, sans téléchargement, garde réseau actif, un seul llama-server à la fois.
- Sous-ensemble du banc, 6 notes copiées de `donnees/demo/notes/` :
  - classiques : `01-xss-reflechi`, `11-kerberoasting`, `16-tls-obsolete` ;
  - difficiles : `22-chemin-bloodhound-court`, `26-partage-trouve-en-scannant`, `29-erreur-etrange-generateur-devis`.

## Indicateurs

- **ok** : le statut mécanique des garde-fous. Ce n'est pas un jugement de qualité.
- **Recopie** : pour chaque fiche et chacune des rubriques titre, description, impact et recommandation, on calcule `difflib.SequenceMatcher(None, texte_fiche, texte_catalogue).ratio()`. Le texte de la fiche est le texte brut produit par le modèle ; le texte du catalogue est celui du constat réellement rattaché, dans la langue du lot. Aucune normalisation. La recopie est la moyenne non pondérée des 24 valeurs.
- **top1 / top3** : rang du `constat_attendu` parmi les candidats de la recherche, sans modèle et de façon déterministe. Ils se mesurent sur les notes 01 à 20 (démo) et 21 à 30 (non vues pendant le réglage).

## Référence (v0.1.0, prompt livré) et seuils v2

| Mesure | v0.1.0 | Seuil v2 |
|---|---|---|
| Rang des notes 01 et 29 | 2e | 1er (CAP-5) |
| top1 / top3, notes 01-20 | — | ≥ 17/20 / 20/20 (CAP-5) |
| top1 / top3, notes 21-30 | — | ≥ 8/10 / 10/10 (CAP-5) |
| Recopie granite | 0,93 (6/6 ok, médiane 17,1 s) | < 0,7, taux ok ≥ 6/6 (CAP-6) |
| Recopie qwen3-1.7b | 0,78 (6/6 ok, médiane 20,4 s) | < 0,7, taux ok ≥ 6/6 (CAP-6) |
| qwen3-1.7b promu défaut | — | ≥ 5/6 ok, recopie < 0,6, médiane < 40 s (CAP-7) |

Leviers du rattachement retenus par les arbitrages : les mots du catalogue et la pondération BM25, réglés sans regarder les notes 21 à 30. Le choix du candidat dans l'UI (CAP-11) sert de filet.

La consigne de départ du réglage est celle de l'essai 3 de `bilan-modeles.md`. Sur qwen3-1.7b, elle donnait une recopie de 0,51, mais seulement 4/6 ok, à cause de l'URL de l'actif retirée (corrigé par CAP-3). Sur granite, elle produisait des boucles de répétition (traitées par CAP-6 avec `repeat_penalty` et par CAP-3 avec le garde-fou de répétition).

Les nouveaux garde-fous (répétition, langue) peuvent faire baisser le taux ok : une baisse due à une vraie sortie dégénérée ou dans une autre langue est consignée comme telle, sans être masquée.
