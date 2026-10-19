# Guide des testeurs — WaveAudit POC

Merci de tester WaveAudit. Ce guide vous installe le POC, vous fait traiter un premier lot de
notes fictives et vous explique comment transmettre votre retour. Toute sortie porte le bandeau
« Démonstration — données fictives » : aucune donnée réelle n'est traitée.

## En bref, ce que vous pouvez faire

- Déposer des notes fictives (vos observations d'audit) et obtenir des fiches de vulnérabilité
  rédigées automatiquement.
- Relire chaque fiche à côté de la note dont elle est issue, la corriger, puis la valider.
- Changer le constat type proposé pour une fiche, ou en choisir un à la main quand aucun ne
  correspond à l'observation.
- Exporter un brouillon Word à tout moment, ou le rapport final une fois les fiches validées.
- Travailler en français ou en anglais.
- Analyser des journaux techniques (connexions, événements Windows) et obtenir un rapport
  d'incident (démonstration CERT).
- Tout se passe sur votre poste : rien n'est envoyé sur Internet pendant le traitement.

## Prérequis

- Windows 11, CPU seul (pas de GPU requis), 16 Go de RAM.
- [uv](https://docs.astral.sh/uv/), qui installera Python 3.12 lui-même si besoin. Aucune
  commande `python`/`pip` globale : tout passe par `uv run`.
- Pas de droits admin ni de compilateur nécessaires.
- Environ 3 Go d'espace disque libre (le moteur et les modèles par défaut : environ 1,6 Go ;
  jusqu'à 3,3 Go si vous installez aussi les modèles candidats en option).

### Installer uv sans droits admin

Dans une invite PowerShell (pas besoin d'administrateur) :

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Ou, si `winget` est disponible sur votre poste :

```
winget install --id=astral-sh.uv -e
```

Fermez ensuite ce terminal et ouvrez-en un nouveau : la commande `uv` n'est reconnue que dans
les terminaux ouverts après son installation. `uv --version` doit alors afficher un numéro de
version.

### Récupérer le dépôt

Avec git :

```
git clone https://github.com/Aliquanto3/waveaudit.git
cd waveaudit
```

Sans git : sur la page GitHub du dépôt, bouton *Code* puis *Download ZIP*, décompressez
l'archive et ouvrez un terminal dans le dossier obtenu.

### Réseau d'entreprise

Seules deux commandes sortent sur Internet : `uv sync` (paquets Python, et Python 3.12 lui-même
s'il manque) et `waveaudit installer` (moteur et modèles). Les principaux domaines contactés
sont `pypi.org` et `files.pythonhosted.org` (paquets Python), `github.com` (moteur et, au
besoin, Python) et `huggingface.co` (modèles) ; les téléchargements sont ensuite redirigés vers
les serveurs de diffusion de ces sites (par exemple `objects.githubusercontent.com` pour GitHub,
d'autres sous-domaines de Hugging Face pour les modèles).

Si votre poste passe par un proxy d'entreprise, définissez-le dans le terminal où vous lancerez
ces deux commandes (le réglage ne vaut que pour ce terminal) :

```powershell
$env:HTTPS_PROXY = "http://proxy:port"
```

Si le proxy inspecte le trafic chiffré (erreur de certificat au téléchargement), il faut
indiquer le certificat racine de votre entreprise. Demandez-le au support informatique, sous
forme de fichier au format PEM (« Base-64 », extension `.pem` ou `.crt`), puis, dans le même
terminal :

```powershell
$env:SSL_CERT_FILE = "C:\chemin\vers\certificat-entreprise.pem"
$env:UV_NATIVE_TLS = "1"
```

`SSL_CERT_FILE` sert aux deux commandes (`uv sync` et `waveaudit installer`) ; `UV_NATIVE_TLS`
permet en plus à `uv` de reprendre les certificats déjà reconnus par Windows.

Si un téléchargement reste bloqué malgré ces réglages, notez-le dans votre retour (voir
« Votre retour » plus bas) avec le message d'erreur exact : votre administrateur réseau pourra
avoir besoin d'ouvrir les domaines cités plus haut.

## Installation (estimation : moins de 10 min, selon votre débit réseau)

```
uv sync                     # installe les dépendances Python, et Python 3.12 si besoin (~1 min)
uv run waveaudit installer  # télécharge moteur + modèles, vérifie leur empreinte (~5-8 min)
```

`uv sync` lit `uv.lock` et télécharge les paquets Python figés (dépôt PyPI) : pas d'autre dépôt,
pas de télémétrie. `waveaudit installer` télécharge le moteur et les poids épinglés du dépôt, et
vérifie leur empreinte (il refuse et supprime tout fichier dont l'empreinte ne correspond pas).
Si une empreinte est refusée, relancez la commande ; si l'échec persiste, c'est un retour à nous
signaler.

## Premier essai dans l'interface

```
uv run waveaudit ui
```

Démarre une interface strictement locale sur `http://127.0.0.1:8765`. Ouvrez cette adresse dans
Edge ou Firefox.

1. À l'accueil, le workflow « Fiches » est déjà sélectionné. Déposez 3 ou 4 notes du dossier
   `donnees/demo/notes` (par exemple `01-xss-reflechi.md`, `02-xss-stocke.md`,
   `03-injection-sql.md`) avec le bouton de sélection de fichiers (`Ctrl`+clic pour en choisir
   plusieurs), puis cliquez « Lancer le lot ».
2. Une barre de progression et un journal apparaissent : le lot est en cours.
3. Une fois le lot terminé, l'écran de relecture s'ouvre automatiquement : votre note d'origine
   à gauche, la fiche générée à droite.
4. Corrigez un champ si besoin (l'enregistrement est automatique, quelques instants après votre
   dernière frappe), puis validez la fiche.
5. Exportez : un bouton permet un brouillon à tout moment, un autre le rapport final une fois
   toutes les fiches validées.

Raccourcis utiles pendant la relecture : `Ctrl+Entrée` pour valider la fiche affichée,
`Ctrl+Alt+↓` et `Ctrl+Alt+↑` pour passer à la fiche suivante ou précédente. Ces deux derniers
ne marchent pas pendant que le curseur est dans un champ de saisie : cliquez d'abord en dehors
des champs (par exemple sur la note à gauche), ou utilisez les boutons « Suivante » et
« Précédente ».

### Parcours détaillé — fiches de bout en bout

1. À l'accueil, choisissez le workflow « Fiches », le modèle par défaut (granite, de l'ordre de
   28 s par fiche) et la langue « Français ». Déposez 6 notes de `donnees/demo/notes`.
   *Résultat attendu : le lot démarre, une barre de progression et un journal apparaissent.*
2. Attendez la fin du lot (terminé, échoué ou interrompu) : l'écran de relecture s'affiche alors
   automatiquement, il ne s'ouvre pas pendant que le lot tourne encore. *Résultat attendu : la
   note source s'affiche à gauche, la fiche générée à droite, un volet latéral liste les
   6 entrées.*
3. Sur une entrée, ouvrez la liste des constats proposés (flèches puis `Entrée` ou `Espace`) et
   choisissez-en un autre que celui retenu. *Résultat attendu : la fiche se régénère sur ce
   choix (« Génération en cours » puis le nouveau texte).*
4. Corrigez un champ d'une autre fiche (par exemple la description). *Résultat attendu :
   l'indicateur passe à « Enregistrement… » puis « Enregistré » quelques instants après votre
   dernière frappe.*
5. Les 30 notes de `donnees/demo/notes` donnent toutes une fiche directement : aucune ne reste
   sans constat proposé. Pour voir ce cas, ajoutez une note hors sujet (par exemple une recette
   de cuisine, sans aucun terme de sécurité), puis sur cette entrée filtrez la liste des constats
   et choisissez-en un à la main. *Résultat attendu : l'entrée ressort sans constat proposé
   automatiquement, puis la fiche se génère sur le choix fait à la main, comme à l'étape 3.*
6. Validez chaque fiche (`Ctrl+Entrée`) et passez à la suivante (`Ctrl+Alt+↓` ou bouton
   « Suivante ») jusqu'à la dernière. *Résultat attendu : chaque fiche validée est repérée comme
   telle dans le volet latéral.*
7. Avant de valider la dernière fiche, cliquez « Exporter un brouillon ». *Résultat attendu : un
   `.docx` se télécharge immédiatement, la fiche non validée y est marquée « non validée ».*
8. Validez la dernière fiche puis cliquez « Exporter ». *Résultat attendu : le rapport final se
   télécharge sans confirmation (toutes les fiches sont validées) ; ouvrez-le dans Word et
   vérifiez la table de synthèse.*

### Parcours détaillé — démo incident (CERT) dans l'interface

1. À l'accueil, choisissez le workflow « Incident », un modèle, puis sélectionnez les fichiers
   de `donnees/demo/incident` (le champ prend plusieurs fichiers, pas un dossier entier) :
   `auth.log`, `syslog`, `security.json`, `system.json`, `sysmon.csv`. *Résultat attendu : le
   lot démarre (pas de choix de langue pour ce workflow, le rapport reste en français).*
2. Une fois terminé, ouvrez le résumé par sévérité et cliquez la carte « Critique ». *Résultat
   attendu : la liste des détections se filtre sur cette sévérité.*
3. Cliquez « Télécharger le rapport ». *Résultat attendu : le `.docx` se télécharge
   immédiatement.*
4. Recommencez l'envoi avec un fichier dont le nom n'est pas reconnu comme journal (par exemple
   `notes.txt`). *Résultat attendu : l'envoi est refusé, aucun lot n'est créé.*

## Pour aller plus loin — la ligne de commande

Pour traiter un lot complet sans passer par l'interface (environ 15 min pour les 30 notes de
démonstration, de l'ordre de 28 secondes par fiche) :

```
uv run waveaudit fiches donnees/demo/notes
```

La commande traite les notes l'une après l'autre et affiche l'avancement, puis le chemin du
rapport Word produit (`var/sorties/<id-du-lot>/rapport.docx`).

Pour un rapport en anglais :

```
uv run waveaudit fiches donnees/demo/notes --langue en
```

Pour réexporter le rapport final d'un lot déjà traité, sans relancer le moteur (ajoutez
`--brouillon` pour un brouillon) :

```
uv run waveaudit exporter <id-du-lot>
```

### Écrire ses propres notes fictives

Un fichier `.md` ou `.txt` par constat, en UTF-8, dans un dossier à vous. En-tête optionnel puis
un corps obligatoire (texte libre : observations, preuves, sorties d'outils) :

```
---
titre: Intitulé libre
actif: URL ou hôte cible
severite_pressentie: elevee   # critique / elevee / moyenne / faible / info
---
Corps de la note : ce que vous avez observé, les preuves (requêtes, sorties d'outils).
```

Seul le corps est obligatoire ; une note sans corps est invalide et ressort dans l'annexe
« Annexe — notes écartées » du rapport. N'utilisez que des données publiques ou fictives.

## Si c'est lent ou bloqué

- Fermez les applications gourmandes en mémoire (le POC vise un pic de 6 Go maximum, suite
  bureautique ouverte) avant un lot complet.
- Sur un poste avec moins de 4,5 Go de RAM libre, WaveAudit choisit automatiquement un modèle
  plus petit et plus rapide (`qwen3.5-0.8b-q4km` au lieu de `granite-4.0-1b-q4km`). Aucun
  message ne l'annonce : dans l'interface, c'est le modèle présélectionné dans la liste
  « Modèle » de l'accueil (la mémoire libre est mesurée à l'affichage de la page). Notez dans
  votre retour le modèle utilisé.
- Une fiche qui dépasse largement 3 min n'est pas bloquée : le modèle tourne sur CPU, laissez-le
  finir. Au-delà de 10 min sans avancement (journal du lot dans l'interface, ou affichage du
  terminal en ligne de commande), arrêtez WaveAudit (`Ctrl+C` dans le terminal) et notez-le
  dans votre retour avec la fiche concernée.
- `uv run waveaudit catalogue verifier` contrôle que le catalogue des constats types est
  intact : utile pour écarter cette cause avant de suspecter le modèle.

## Ce qui sort, ou non, du poste

Aucun appel réseau sortant n'a lieu pendant l'utilisation de l'interface ou le traitement d'un
lot : un garde réseau du dépôt bloque toute connexion qui ne serait pas vers votre propre
machine (vérifié par un test automatisé). Seules `uv sync` et `waveaudit installer`, à
l'installation, appellent l'extérieur. Vos notes, fictives, et les rapports générés restent dans
votre dossier et dans `var/` : rien n'est envoyé ailleurs.

## Votre retour

Merci de remplir une issue GitHub avec le modèle « Retour testeur » (menu *New issue* du dépôt).
Indiquez-y la version testée, affichée par `uv run waveaudit version` (`waveaudit 0.2.0rc1` ou
plus récent pour cette campagne). Cela demande un compte GitHub ; si vous n'en avez pas, envoyez le même contenu par mail à la
personne qui vous a invité à tester.

Jamais de données réelles de mission, ni dans vos notes de test, ni dans votre retour :
uniquement des données publiques ou fictives.
