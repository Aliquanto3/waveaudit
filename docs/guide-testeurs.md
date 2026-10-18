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

`uv sync` lit `uv.lock` et télécharge les paquets Python figés (dépôt PyPI) : pas d'autre dépôt,
pas de télémétrie.
`waveaudit installer` télécharge `llama-server` et les poids épinglés du manifeste
(`config/artefacts.toml`) dans `var/`, vérifie leur empreinte SHA-256 et refuse (en la
supprimant) toute empreinte incorrecte. Si une empreinte est refusée, relancez la commande ;
si l'échec persiste, c'est un retour à nous signaler (voir plus bas).

## Premier lot, sur les notes de démonstration (estimation : moins de 3 min par fiche)

Le dépôt contient 30 notes fictives dans `donnees/demo/notes/`. La commande ci-dessous traite le
dossier complet ; pour un premier essai plus court, copiez-en quelques-unes dans un dossier à part
et pointez la commande sur ce dossier à la place :

```
uv run waveaudit fiches donnees/demo/notes
```

La commande traite les notes l'une après l'autre dans le terminal (synchrone) et affiche
l'avancement note par note, puis le chemin du rapport Word produit
(`var/sorties/<id-du-lot>/rapport.docx`). Sur CPU, la première fiche d'un lot est plus lente
(chargement du modèle en mémoire), les suivantes sont plus régulières.

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

Seul le corps est obligatoire ; une note sans corps est invalide et ressort dans l'annexe
« Notes écartées » du rapport. N'utilisez que des données publiques ou fictives.

## Lancer l'interface web

```
uv run waveaudit ui
```

Démarre une interface strictement locale sur `http://127.0.0.1:8765` (changez de port avec
`--port` en cas de conflit). Elle n'accepte que les requêtes dont l'en-tête `Host`/`Origin` vise
la boucle locale.

### Parcours de Camille — fiches de bout en bout

1. À l'accueil, choisissez le workflow « Fiches », le modèle par défaut (granite, ~28 s/fiche)
   et la langue « Français ». Déposez 6 notes de `donnees/demo/notes` (glisser-déposer ou
   sélecteur de fichiers). *Résultat attendu : le lot démarre, une barre de progression et un
   journal apparaissent.*
2. Attendez la fin du lot (terminé, échoué ou interrompu) : l'écran de relecture s'affiche alors
   automatiquement, il ne s'ouvre pas pendant que le lot tourne encore. *Résultat attendu : la
   note source s'affiche à gauche, la fiche générée à droite, un tiroir liste les 6 entrées.*
3. Sur une entrée, ouvrez la barre des candidats (flèches puis `Entrée`/`Espace`) et choisissez
   un autre constat que celui retenu. *Résultat attendu : la fiche se régénère sur ce candidat
   (« Génération en cours » puis le nouveau texte).*
4. Corrigez un champ d'une autre fiche (ex. la description). *Résultat attendu : l'indicateur
   passe à « Enregistrement… » puis « Enregistré » quelques instants après la dernière frappe.*
5. Les 30 notes de `donnees/demo/notes` sont toutes rattachables : aucune n'est non rattachée.
   Pour obtenir une entrée non rattachée, ajoutez au dépôt une note hors sujet (par exemple une
   recette de cuisine, sans aucun terme de sécurité), puis sur cette entrée filtrez le catalogue
   et choisissez un constat à la main. *Résultat attendu : l'entrée ressort non rattachée (pas
   de génération automatique), puis la fiche se génère sur le constat choisi, comme à l'étape 3.*
6. Validez chaque fiche (`Ctrl+Entrée`) et passez à la suivante (`Ctrl+Alt+↓` ou bouton
   « Suivante ») jusqu'à la dernière. *Résultat attendu : chaque fiche validée est repérée comme
   telle dans le tiroir.*
7. Avant de valider la dernière fiche, cliquez « Exporter un brouillon ». *Résultat attendu : un
   `.docx` se télécharge immédiatement, la fiche non validée y est marquée « non validée ».*
8. Validez la dernière fiche puis cliquez « Exporter ». *Résultat attendu : le rapport final se
   télécharge sans confirmation (toutes les fiches sont validées) ; ouvrez-le dans Word et
   vérifiez la table de synthèse.*

### Parcours de Karim — démo CERT dans l'UI

1. À l'accueil, choisissez le workflow « Incident », un modèle, puis sélectionnez les fichiers
   de `donnees/demo/incident` (le champ prend plusieurs fichiers, pas un dossier entier) :
   `auth.log`, `syslog`, `security.json`, `system.json`, `sysmon.csv`. *Résultat attendu : le
   lot démarre (pas de choix de langue pour ce workflow, le rapport reste en français).*
2. Une fois terminé, ouvrez le résumé par sévérité et cliquez la carte « Critique ». *Résultat
   attendu : la liste des détections se filtre sur cette sévérité.*
3. Cliquez « Télécharger le rapport ». *Résultat attendu : le `.docx` se télécharge
   immédiatement.*
4. Recommencez l'envoi avec un fichier dont le nom n'est pas reconnu comme journal (ex.
   `notes.txt` : ni `.json`, ni `.csv`, ni `.log`/`auth.log`/`syslog`/`secure`). *Résultat
   attendu : l'envoi est refusé (`aucun_journal_reconnu`), aucun lot n'est créé.*

## Points à vérifier en recette

- Bascule entre les workflows « Fiches » et « Incident » à l'accueil, et message
  `aucun_journal_reconnu` sur un dépôt sans journal reconnu.
- Parcours clavier complet de la relecture : flèches dans le tiroir, onglets de candidats,
  `Ctrl+Entrée` (valider), `Ctrl+Alt+↓`/`↑` (naviguer), `Échap` (fermer un dialogue, focus rendu
  au bouton qui l'a ouvert), piège de focus dans un dialogue ouvert (Tab/Maj+Tab bouclent sur
  ses boutons).
- Indicateur d'enregistrement d'un champ corrigé : « Enregistrement… » puis « Enregistré »
  quelques instants après la dernière frappe, et annonces lues par un lecteur d'écran
  (`aria-live`).
- Deux onglets ouverts sur la même fiche : corriger un champ dans les deux doit ouvrir le
  dialogue de conflit sur le second ; vérifier `Échap` (dialogue fermé sans choix, la saisie
  suivante le rouvre), « Garder ma version » et « Recharger ».
- Serveur arrêté (ou coupure réseau locale) pendant une saisie en cours d'enregistrement :
  message de réessai affiché, reprise une fois le serveur revenu.
- Changement de candidat sur une fiche déjà corrigée ou déjà validée : confirmation demandée ;
  une fois confirmé, « Génération en cours » puis la fin de régénération annoncée.
- Export final avec des fiches non validées (confirmation demandée) et export d'un brouillon à
  tout moment (téléchargement immédiat par `Blob`, sans confirmation).
- Lien « Télécharger le rapport » affiché dès que le lot est terminé, sur l'écran de suivi.
- Attribut `lang` du panneau de relecture passé à l'anglais sur un lot traité en anglais
  (`--langue en` ou choix « English » à l'accueil).
- Dialogues de confirmation et de conflit : vérifier qu'ils sont bien opaques (pas de contenu
  de la page visible en transparence derrière).
- Repli du tiroir de relecture sous 1440 px de large.
- Arrêt de l'UI (Ctrl+C) pendant un lot en cours, puis `tasklist | findstr llama-server` dans un
  terminal : aucune ligne ne doit apparaître.
- Repli sur le modèle `qwen3.5-0.8b` avec peu de RAM disponible (fermer la suite bureautique
  avant de lancer un lot, ou limiter la RAM visible par le poste).
- Relecture des 10 constats traduits de Q3 (liste dans
  `_bmad-output/implementation-artifacts/etat-v2.md`, section « Relecture de Q3 ») sur un
  rapport Word exporté en anglais.

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
toute connexion hors boucle locale (vérifié par un test automatisé du dépôt). `sbom`
(`uv run waveaudit sbom`) liste les paquets installés dans `var/sbom.cdx.json` en lisant
uniquement votre venv local, sans appel réseau non plus. Seules `uv sync` et `waveaudit
installer`, à l'installation, appellent l'extérieur (dépôts de paquets et de modèles). Vos
notes, fictives, et les rapports générés restent dans votre dossier et dans `var/` : rien n'est
envoyé ailleurs.

## Votre retour

Merci de remplir une issue GitHub avec le modèle « Retour testeur » (menu *New issue* du dépôt) :
machine utilisée, temps d'installation, temps par fiche, et pour chaque fiche une note
« utilisable / retouches légères / à refaire », plus tout besoin, idée ou constat type manquant.
