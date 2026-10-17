# Guide des testeurs — WaveAudit POC

Merci de tester WaveAudit. Ce guide vous installe le POC, vous fait traiter un premier lot de
notes fictives et vous explique comment transmettre votre retour. Toute sortie porte le bandeau
« Démonstration — données fictives » : aucune donnée réelle n'est traitée.

## Prérequis

- Windows 11, CPU seul (pas de GPU requis), 16 Go de RAM.
- [Python 3.12](https://www.python.org/) et [uv](https://docs.astral.sh/uv/) installés. Aucune
  commande `python`/`pip` globale : tout passe par `uv run`.
- Pas de droits admin ni de compilateur nécessaires.

## Installation (estimation : moins de 10 min, selon votre débit réseau)

```
git clone https://github.com/Aliquanto3/waveaudit.git
cd waveaudit
uv sync                     # installe les dépendances Python (~1 min)
uv run waveaudit installer  # télécharge moteur + modèles, vérifie leur empreinte (~5-8 min)
```

`uv sync` lit `uv.lock` : les versions sont figées, rien d'autre n'est appelé sur le réseau.
`waveaudit installer` télécharge `llama-server` et les poids épinglés du manifeste
(`config/artefacts.toml`) dans `var/`, vérifie leur empreinte SHA-256 et refuse (en la
supprimant) toute empreinte incorrecte. Si une empreinte est refusée, relancez la commande ;
si l'échec persiste, c'est un retour à nous signaler (voir plus bas).

## Premier lot, sur les notes de démonstration (estimation : moins de 3 min par fiche)

Le dépôt contient 30 notes fictives dans `donnees/demo/notes/`. Pour un premier essai rapide,
traitez-en quelques-unes seulement (copiez-les dans un dossier à part) avant un lot complet :

```
uv run waveaudit fiches donnees/demo/notes
```

La commande affiche l'avancement note par note, puis le chemin du rapport Word produit
(`var/sorties/<id-du-lot>/rapport.docx`). Sur CPU, chaque fiche se génère en arrière-plan : la
première fiche d'un lot est plus lente (chargement du modèle en mémoire), les suivantes sont
plus régulières.

## Ouvrir le rapport

Ouvrez le `.docx` indiqué dans Word. Chaque fiche porte : titre, description, impact,
recommandation, vecteur et score CVSS 3.1, références (uniquement celles du catalogue, jamais
inventées), statut (`ok` ou `à revoir` avec son motif) et la traçabilité (fichier de note
source, constat type retenu). Le bandeau « Démonstration — données fictives » figure en tête et
en pied de document.

## Écrire ses propres notes fictives

Un fichier `.md` ou `.txt` par constat, en UTF-8, dans un dossier à vous. En-tête YAML optionnel
puis un corps obligatoire (texte libre : observations, preuves, sorties d'outils) :

```
---
titre: Intitulé libre
actif: URL ou hôte cible
severite_pressentie: elevee   # critique / elevee / moyenne / faible / info
---
Corps de la note : ce que vous avez observé, les preuves (requêtes, sorties d'outils).
```

Seul le corps est obligatoire ; une note sans corps est invalide et ressort en « entrée
écartée ». N'utilisez que des données publiques ou fictives.

## Lancer l'interface web

```
uv run waveaudit ui
```

Démarre une interface strictement locale sur `http://127.0.0.1:8765` (changez de port avec
`--port` en cas de conflit). On y dépose un dossier de notes, on suit la progression du lot en
direct, puis on télécharge le rapport une fois terminé. Elle n'accepte que les requêtes dont
l'en-tête `Host`/`Origin` vise la boucle locale.

## Si c'est lent ou bloqué

- Fermez les applications gourmandes en mémoire (le POC vise un pic ≤ 6 Go, suite bureautique
  ouverte) avant un lot complet.
- Une fiche qui dépasse largement 3 min n'est pas bloquée : le modèle tourne sur CPU, laissez-le
  finir. Au-delà de 10 min sans avancement dans la console, interrompez (Ctrl+C) et notez-le
  dans votre retour avec la fiche concernée.
- `uv run waveaudit catalogue verifier` contrôle que le catalogue est en cause avant de suspecter
  le modèle.

## Ce qui sort, ou non, du poste

Aucun appel réseau sortant n'a lieu pendant `fiches`, `ui` ou `banc` : un garde réseau bloque
toute connexion hors boucle locale (vérifié par un test automatisé du dépôt). Seules `uv sync`
et `waveaudit installer`, à l'installation, appellent l'extérieur (dépôts de paquets et de
modèles). Vos notes, fictives, et les rapports générés restent dans votre dossier et dans
`var/` : rien n'est envoyé ailleurs.

## Votre retour

Merci de remplir une issue GitHub avec le modèle « Retour testeur » (menu *New issue* du dépôt) :
machine utilisée, temps d'installation, temps par fiche, et pour chaque fiche une note
« utilisable / retouches légères / à refaire », plus tout besoin, idée ou constat type manquant.
