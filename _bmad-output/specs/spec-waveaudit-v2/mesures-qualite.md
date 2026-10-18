# Mesures de qualité v2 (CAP-5 à CAP-7)

Le protocole reprend celui de `bilan-modeles.md`. Les résultats y sont consignés.

## Poste et protocole

- Poste : l'EliteBook cible (i5-1145G7, 4 cœurs physiques, 15,7 Gio, Windows 11), llama-server en CPU, `threads = 4`, `ctx = 4096`.
- Commande : `uv run waveaudit banc var/banc-sous-ensemble --modele <nom> --seed <s>`, sans téléchargement, garde réseau actif, un seul llama-server à la fois.
- Seeds : 42, 142 et 242 pour chaque modèle (3 lots par modèle). Les seeds sont espacées pour ne pas recouper la seed de la nouvelle tentative (`seed + 1`, CAP-1).
- Sous-ensemble du banc, 6 notes copiées de `donnees/demo/notes/` :
  - classiques : `01-xss-reflechi`, `11-kerberoasting`, `16-tls-obsolete` ;
  - difficiles : `22-chemin-bloodhound-court`, `26-partage-trouve-en-scannant`, `29-erreur-etrange-generateur-devis`.

## Indicateurs

- **ok** : le statut mécanique des garde-fous. Ce n'est pas un jugement de qualité. Pour le critère de CAP-6, une fiche `a_revoir` dont les seuls motifs sont `repetition` ou `langue`, et qu'une relecture à la main confirme dégénérée ou dans une autre langue, n'est pas décomptée ; chaque cas est consigné avec la fiche en cause.
- **Recopie** (une seule définition, celle de la référence 0,93) : pour chaque fiche qui n'est pas un repli et chacune des rubriques titre, description, impact et recommandation, on calcule `difflib.SequenceMatcher(None, texte_fiche, texte_catalogue).ratio()`, `autojunk` à sa valeur par défaut. Le texte de la fiche est le texte produit par le modèle tel qu'écrit dans `fiches.json` (le « texte brut » de `bilan-modeles.md`) ; le texte du catalogue est celui du constat réellement rattaché, dans la langue du lot. Aucune normalisation. La recopie est la moyenne non pondérée de ces valeurs. Les replis (motifs `repli_sortie_invalide` ou `repli_moteur`, texte du catalogue par construction) sont comptés à part (`replis`) et n'entrent pas dans la moyenne.
- **top1 / top3** : rang du `constat_attendu` parmi les candidats de la recherche, sans modèle et de façon déterministe. Ils se mesurent sur les notes 01 à 20 (démo) et sur les notes « non vues » 21 à 28 et 30. La note 29, cible du réglage, ne fait pas partie des notes non vues.
- **Agrégation sur 3 seeds** : `bilan-modeles.md` publie, par modèle, le minimum et la médiane de `ok`, la médiane et le maximum de la recopie, la médiane des durées médianes par fiche.

## Référence (v0.1.0, prompt livré) et seuils v2

| Mesure | v0.1.0 | Seuil v2 |
|---|---|---|
| Rang des notes 01 et 29 | 2e | 1er (CAP-5) |
| top1 / top3, notes 01-20 | — | ≥ 17/20 / 20/20 (CAP-5) |
| top1 / top3, notes 21-28 et 30 | — | ≥ 8/9 / 9/9 (CAP-5) |
| Recopie granite | 0,93 (6/6 ok, médiane 17,1 s, 1 seed) | médiane < 0,7 ; sur chaque seed, ok ≥ 6/6 hors `repetition`/`langue` confirmés (CAP-6) |
| Recopie qwen3-1.7b | 0,78 (6/6 ok, médiane 20,4 s, 1 seed) | médiane < 0,7 ; sur chaque seed, ok ≥ 6/6 hors `repetition`/`langue` confirmés (CAP-6) |
| qwen3-1.7b promu défaut | — | médianes : ≥ 5/6 ok, recopie < 0,6, durée < 40 s (CAP-7) |
| Garde de CI longue (`slow`) | — | banc réel sur 2 notes, modèle par défaut : recopie ≤ 0,8 (plafond contre un retour vers 0,93, pas le seuil de CAP-6) |

## Réglage du rattachement (CAP-5)

Leviers retenus par les arbitrages : les mots du catalogue et la pondération BM25, réglés sans regarder les notes 21 à 30. Pendant le réglage, le test des notes non vues est en `xfail` et n'est pas lu ; le verrou est levé une seule fois, en fin de story, et les valeurs obtenues sont figées dans le message de commit avec les essais et leur score sur 01-20. Si le seuil des notes non vues n'est pas atteint à ce moment, la story s'arrête et le signale à Anaël : on ne relance pas le réglage en regardant ces notes. Le choix du candidat dans l'UI (CAP-11) sert de filet.

## Consigne (CAP-6)

La consigne de départ du réglage est celle de l'essai 3 de `bilan-modeles.md`. Sur qwen3-1.7b, elle donnait une recopie de 0,51, mais seulement 4/6 ok, à cause de l'URL de l'actif retirée (corrigé par CAP-3). Sur granite, elle produisait des boucles de répétition (traitées par CAP-6 avec `repeat_penalty` et par CAP-3 avec le garde-fou de répétition).

Les nouveaux garde-fous (répétition, langue) peuvent faire baisser le taux ok : une baisse due à une vraie sortie dégénérée ou dans une autre langue est consignée comme telle, sans être masquée.
