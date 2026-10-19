# WaveAudit

[![CI](https://github.com/Aliquanto3/waveaudit/actions/workflows/ci.yml/badge.svg)](https://github.com/Aliquanto3/waveaudit/actions/workflows/ci.yml)

Assistant IA **hors ligne** pour les consultants en audit de cybersécurité, sur un PC professionnel de 16 Go sans GPU. Il rédige des **fiches de vulnérabilité** à partir des notes brutes du consultant, en retrouvant le constat type dans un catalogue puis en l'adaptant au contexte. Aucune donnée ne quitte le poste.

> **État : POC v2 en test (version candidate 0.2.0).** Il ne traite que des données publiques ou fictives ; toute sortie porte le bandeau « Démonstration — données fictives ».

## Ce que fait WaveAudit

- Déposer des notes d'audit fictives et obtenir des fiches de vulnérabilité rédigées automatiquement.
- Relire chaque fiche à côté de sa note source, la corriger, puis la valider, dans une interface web locale.
- Changer le constat type proposé pour une fiche, ou en choisir un à la main dans le catalogue.
- Exporter un brouillon Word à tout moment, ou le rapport final une fois les fiches validées.
- Rédiger les fiches en français ou en anglais.
- Analyser des journaux techniques (connexions, événements Windows) et produire un rapport d'incident (démonstration CERT).

> **Vous testez le POC ?** Suivez le [guide des testeurs](docs/guide-testeurs.md) : installation,
> premier lot, et comment transmettre votre retour.

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
| Qualité | ≥ 70 % de fiches utilisables après retouches légères (notes fictives) |
| Fiabilité | 0 référence inventée |
| Vitesse | < 3 min par fiche sur un portable 16 Go, suite bureautique ouverte |
| Mémoire | Pic ≤ 6 Go |
| Installation | < 10 min |

## Prérequis

- Windows 11, CPU seul (pas de GPU requis), 16 Go de RAM.
- [uv](https://docs.astral.sh/uv/), qui installe Python 3.12 lui-même au besoin (aucun `python`
  ni `pip` global : toutes les commandes passent par `uv run`). Installation sans droits admin,
  et clonage possible par simple téléchargement du ZIP GitHub sans git : détail dans le
  [guide des testeurs](docs/guide-testeurs.md#récupérer-le-dépôt).
- Pas de droits admin ni de compilateur nécessaires.
- Sur un réseau d'entreprise avec proxy, voir le
  [guide des testeurs](docs/guide-testeurs.md#réseau-dentreprise).

## Installation

```
git clone https://github.com/Aliquanto3/waveaudit.git
cd waveaudit
uv sync
uv run waveaudit installer
```

`uv sync` installe les dépendances Python épinglées (`uv.lock`). `waveaudit installer` télécharge
`llama-server` et les poids épinglés du manifeste (`config/artefacts.toml`) dans `var/`, vérifie
leur empreinte SHA-256 et refuse (en la supprimant) toute empreinte incorrecte. `--candidats`
télécharge en plus les modèles candidats du manifeste.

## Utilisation — CLI

```
uv run waveaudit fiches <dossier-de-notes> [-o FICHIER] [--modele NOM] [--langue fr|en] [--config FICHIER]
```

Traite les notes `.md`/`.txt` du dossier et produit un rapport Word de fiches de vulnérabilité
dans `var/sorties/<id-du-lot>/rapport.docx` (et, avec `-o`, une copie supplémentaire). `--modele`
choisit un modèle du manifeste (mode `local-gere`) ou surcharge le nom envoyé à l'API (mode
`externe`). `--langue` choisit la langue des fiches et du rapport (défaut : configuration).
`--config` ajoute un fichier TOML de configuration supplémentaire.

Exporter à nouveau le rapport d'un lot déjà traité, final ou brouillon, sans relancer le moteur :

```
uv run waveaudit exporter <id-du-lot> [--brouillon] [--config FICHIER]
```

Autres commandes (`uv run waveaudit --help` pour le détail) :

| Commande | Rôle |
|---|---|
| `installer [--candidats]` | Télécharge et vérifie les artefacts du manifeste |
| `fiches DOSSIER [--langue fr\|en] [...]` | Lot CLI décrit ci-dessus |
| `incident DOSSIER [--annee N] [...]` | Analyse de journaux CERT décrite ci-dessous (toujours en français) |
| `ui [--port N] [--config F]` | Démarre l'interface web locale |
| `banc DOSSIER [--modele NOM] [--langue fr\|en]` | Lot instrumenté (temps par fiche, pic mémoire, recopie) |
| `exporter LOT [--brouillon] [--config F]` | Exporte en Word le rapport final ou le brouillon d'un lot |
| `catalogue verifier [--config F]` | Contrôle le catalogue de constats types |
| `sbom` | Écrit le SBOM (CycloneDX) de l'environnement installé |
| `version` | Affiche la version installée |

Codes retour (`uv run waveaudit <commande> ...; echo $?`) : `0` lot terminé, `2` entrée ou
configuration invalide (dont `--modele` inconnu), `3` moteur injoignable, `4` connexion interdite
ou permission refusée (ex. `-o` sur un fichier verrouillé), `5` empreinte d'artefact invalide.

## Utilisation — interface web

```
uv run waveaudit ui
```

Démarre une interface web strictement locale (`http://127.0.0.1:8765` par défaut, `--port` pour
changer). Elle n'accepte que les requêtes dont l'en-tête `Host` et `Origin` visent la boucle
locale. À l'accueil, on choisit le workflow (fiches ou incident), le modèle et la langue (fr/en,
fiches seulement), puis on dépose les fichiers. On suit la progression du lot en direct, on
relit et corrige chaque fiche à l'écran, on change de candidat si besoin, puis on télécharge le
rapport Word final ou un brouillon. Interrompre l'UI (Ctrl+C) arrête proprement le llama-server
en cours et marque un lot en cours `interrompu` (les fiches déjà produites restent relisibles et
exportables).

## Utilisation — CERT (analyse d'incident)

```
uv run waveaudit incident <dossier-de-journaux> [-o FICHIER] [--annee N] [--modele NOM] [--config FICHIER]
```

Lit les journaux (auth/syslog Linux, journal Windows exporté en JSON, Sysmon en CSV) d'un
dossier, détecte les faits connus d'un catalogue de règles, puis fait rédiger à chaque fait
détecté un récit en français (titre, récit, impact, recommandation) par le même moteur que
`fiches`. Produit `var/sorties/<id-du-lot>/incident.json` (le rapport structuré) et
`rapport-incident.docx` (et, avec `-o`, une copie supplémentaire). `--annee` complète les
journaux sans année explicite dans leurs horodatages (année courante par défaut). Sans aucun
fait détecté, le rapport l'indique et le moteur n'est jamais ouvert (code 0, même si le moteur
est injoignable). Ce rapport reste en français, en CLI comme dans l'UI.

Dans l'interface web, le workflow « Incident » refuse à l'envoi un dépôt sans journal reconnu
(`aucun_journal_reconnu`) : aucun lot n'est créé. Un dépôt reconnu mais sans aucune détection
produit un rapport téléchargeable qui l'indique (« Aucune détection sur ce dépôt »).

Le dossier `donnees/demo/incident/` fournit un jeu de démonstration (données fictives) :

```
uv run waveaudit incident donnees/demo/incident --annee 2026
```

Limites connues :

- Décalage horaire fixe pour les journaux syslog (pas d'heure d'été) : pour un incident à cheval
  sur un changement d'heure, lancer deux analyses séparées.
- Exports de journal Windows : `ConvertTo-Json` brut de PowerShell 5.1 ne donne ni la propriété
  `Data` ni un horodatage ISO ; utiliser plutôt le script PowerShell ci-dessous.
- Indicateurs extraits des journaux : une adresse IPv4 suivie d'un point final dans le message
  d'une ligne (« depuis 203.0.113.5. ») n'est pas relevée. Les garde-fous du récit, eux, traitent
  ce cas.
- Garde-fous du récit : un mot qui a la forme d'une adresse IPv6 valide (« cafe::dead », « :: »)
  et qui n'apparaît pas dans les journaux est retiré du récit comme indicateur inventé ; le récit
  passe alors « à revoir ».
- Aucun coupe-circuit sur le moteur : s'il tombe en cours d'analyse, il est rappelé pour chaque
  détection restante, et chaque récit concerné reprend le texte type de la règle (« à revoir »).
- Lecture des journaux non en flux : chaque fichier est chargé en mémoire en entier.

Export d'un journal d'événements Windows au format normalisé attendu (PowerShell 5.1 ; le
journal `Security` demande une console administrateur). Le lecteur exige un tableau JSON
d'objets portant `TimeCreated` (ISO 8601 avec fuseau), `Id`, `MachineName` et `Data` (objet des
champs `EventData`) ; `LogName` sert aux règles :

```powershell
$evenements = Get-WinEvent -LogName Security -MaxEvents 5000 | ForEach-Object {
    $xml = [xml]$_.ToXml()
    $data = [ordered]@{}
    foreach ($champ in $xml.Event.EventData.Data) {
        if ($champ.Name) { $data[$champ.Name] = $champ.'#text' }
    }
    [PSCustomObject]@{
        TimeCreated  = $_.TimeCreated.ToString("o")
        Id           = $_.Id
        LogName      = $_.LogName
        ProviderName = $_.ProviderName
        MachineName  = $_.MachineName
        Message      = $_.Message
        Data         = $data
    }
}
ConvertTo-Json -InputObject @($evenements) -Depth 4 | Out-File security.json -Encoding utf8
```

`-InputObject @(...)` garde un tableau même pour un seul événement (le pipeline donnerait un
objet seul, que le lecteur ignore).

## Preuve hors ligne

- **Aucun appel réseau sortant à l'exécution** (hors `uv sync` et `waveaudit installer`, qui
  n'ont lieu qu'à l'installation) : un garde réseau (`securite/garde_reseau.py`) remplace les
  fonctions de connexion du module `socket` pendant les commandes `fiches`, `incident`, `ui` et
  `banc`, et
  lève une erreur avant toute connexion vers un hôte hors boucle locale.
  `tests/e2e/test_hors_ligne.py` exécute un lot CLI et un lot UI complets sous ce garde et vérifie
  qu'aucune tentative n'a été refusée, puis prouve, à l'inverse, que le garde détecte et bloque
  une tentative de connexion sortante faite par un abonné du lot.
- **SHA-256** : chaque artefact téléchargé par `waveaudit installer` (moteur, modèles) est vérifié
  contre l'empreinte du manifeste (`config/artefacts.toml`), qui documente aussi sa source et sa
  licence ; une empreinte incorrecte est refusée et le fichier supprimé.
- **SBOM** : `uv run waveaudit sbom` écrit un inventaire CycloneDX des dépendances installées
  dans `var/`, pour l'audit.
- **Suite de tests** : `uv run pytest -q` n'utilise jamais le vrai modèle ni le réseau (faux
  moteur HTTP local). Seuls les tests marqués `slow` (`tests/e2e/test_reel.py`, lot de bout en
  bout sur 2 notes de démonstration, et `tests/e2e/test_llama_reel.py`) lancent le vrai
  `llama-server` ; ils sont exclus par défaut (`-m 'not slow'`), et sautés tant que
  `waveaudit installer` n'a pas été lancé.

## Choix et licences des modèles

Les artefacts installés sont épinglés par version et empreinte dans `config/artefacts.toml` :

| Rôle | Modèle | Licence | Source |
|---|---|---|---|
| Moteur | llama-server (llama.cpp) | MIT | github.com/ggml-org/llama.cpp |
| Modèle par défaut | Granite 4.0 1B (GGUF Q4_K_M) | Apache-2.0 | huggingface.co/ibm-granite |
| Modèle de repli (RAM basse) | Qwen3.5 0.8B (GGUF Q4_K_M) | Apache-2.0 | huggingface.co/unsloth |
| Candidats (choisissables à l'accueil) | Qwen3 1.7B, MiniCPM5 1B (GGUF Q4_K_M) | Apache-2.0 | huggingface.co/unsloth, huggingface.co/openbmb |

Tous sous licence permissive. `repeat_penalty = 1.1` pour granite et qwen3-1.7b. Sans `--modele`
ni modèle choisi à l'accueil, granite (par défaut) n'est retenu que si la RAM disponible au
lancement est ≥ 4,5 Go (`ram_min_defaut_go`, `config/waveaudit.toml`) ; sous ce seuil, repli
automatique sur qwen3.5-0.8b. Seuil fixé au POC, non remesuré en v2.

Rebanc EliteBook (v2, détail dans
`_bmad-output/implementation-artifacts/bilan-modeles.md`) : **granite-4.0-1b reste le modèle
par défaut**, sur arbitrage — il tient le critère CAP-6 (6/6 fiches ok sur 3 seeds, recopie
médiane 0,56, médiane 27,9 s/fiche). **qwen3-1.7b** adapte davantage (recopie 0,45) mais, à une
seed, une fiche sort en repli sur un délai dépassé (5/6, CAP-6 non tenu) ; il reste candidat,
choisissable à l'accueil. qwen3.5-0.8b (repli) et minicpm5-1b (candidat) n'ont pas été rebancés
en v2.

Mesure de la recherche du constat type (Q4, index bilingue) : les notes 01 et 29 ont servi au
réglage des mots-clés (optimiste) et atteignent le rang 1. Sur les notes non vues du banc
(21-28 et 30, 9 notes), le bon constat sort en rang 1 dans 8 cas sur 9 (top1) et dans les 3
premiers dans 9 cas sur 9 (top3).

## Banc

```
uv run waveaudit banc <dossier-de-notes> [--modele NOM]
```

Exécute un lot instrumenté (contrats §20) : il échantillonne, toutes les 0,5 s, le pic de mémoire
RSS de l'application et du moteur pendant le lot, et écrit `var/sorties/<id>/banc.json` (durée
médiane et maximale par fiche, pics mémoire, top des constats et de leurs étiquettes) ainsi qu'un
résumé lisible en console. Avec le faux moteur (tests), il s'exécute en test rapide ; les seuils
réels (< 3 min/fiche, pic ≤ 6 Go) se vérifient hors nuit, sur le poste cible.

## Limites du POC

- Sortie Word, par lot ; la correction d'une fiche se fait dans l'écran de relecture de l'UI
  (pas de chat), l'export final liste en annexe les fiches restées non validées.
- Jamais de génération ex nihilo : toute fiche part d'un constat type du catalogue ; aucune
  référence absente du catalogue.
- Rapport de fiches en français ou en anglais (`--langue`, ou choix à l'accueil de l'UI) ;
  rapport d'incident toujours en français, y compris ses codes bruts d'annexe.
- Données publiques ou fictives seulement ; le bandeau « Démonstration — données fictives »
  figure sur toute sortie.
- Pas de chat interactif, pas d'assistant bureautique générique, pas de fine-tuning, pas de
  génération d'exploits, pas d'import des formats d'outils (Burp, Nessus), pas d'usage
  multi-utilisateur ni serveur.
- Pas de verrou inter-processus entre un lot CLI et un lot UI : les lancer en même temps peut
  charger un second llama-server. Un lot CLI en cours apparaît en lecture seule dans l'UI et est
  refusé par `waveaudit exporter`. Le moteur est relancé à la première régénération après un lot.
- Arrêt de l'UI (Ctrl+C) : le llama-server est tué, en moins de 15 s mesurées en test. Sous un
  système autre que Windows, cette borne n'est pas garantie au pire cas (dépend du délai
  d'arrêt du processus moteur).
- Régénérer une fiche d'un lot depuis une autre instance de l'UI (deux processus sur le même
  dossier) n'est pas détecté : le verrou de régénération n'est vu que dans le processus qui l'a
  posé. Le document exporté n'en est pas affecté (la fiche courante reste celle d'avant la
  régénération).
- Toute donnée client réelle est hors périmètre.

## Contenu du dépôt

- `_bmad-output/forge/slm-edge-consultants-cyber/` : cadrage de l'idée (`forged-idea.md`) et rapport de la session (`forge-report.html`).
- `_bmad-output/specs/`, `_bmad-output/planning-artifacts/` : spécifications et architecture du POC.
- `_bmad/`, `.claude/skills/` : méthode [BMAD](https://github.com/bmad-code-org/BMAD-METHOD) pour la spécification et le développement.
- `.claude/cost-kit/` : contrôle rapide de [agent-cost-kit](https://github.com/Aliquanto3/agent-cost-kit).
- `theme-prive/` (ignoré par git, absent du dépôt public) : charte et logo Wavestone pour le
  thème du rapport Word (`modele.docx`) et de l'UI (`theme-prive/web/logo.svg`) ; le dépôt
  fonctionne sans lui (thème générique, palette publique Wavestone, sans logo).

## Licence

[Apache 2.0](LICENSE).
