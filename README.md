# WaveAudit

[![CI](https://github.com/Aliquanto3/waveaudit/actions/workflows/ci.yml/badge.svg)](https://github.com/Aliquanto3/waveaudit/actions/workflows/ci.yml)

Assistant IA **hors ligne** pour les consultants en audit de cybersécurité, sur un PC professionnel de 16 Go sans GPU. Il rédige des **fiches de vulnérabilité** à partir des notes brutes du consultant, en retrouvant le constat type dans un catalogue puis en l'adaptant au contexte. Aucune donnée ne quitte le poste.

> **État : POC en développement.** Il ne traite que des données publiques ou fictives ; toute sortie porte le bandeau « Démonstration — données fictives ».

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

> **Vous testez le POC ?** Suivez le [guide des testeurs](docs/guide-testeurs.md) : installation,
> premier lot, et comment transmettre votre retour.

## Prérequis

- Windows 11, CPU seul (pas de GPU requis), 16 Go de RAM.
- [Python 3.12](https://www.python.org/) et [uv](https://docs.astral.sh/uv/) (aucun `python` ni `pip` global : toutes les commandes passent par `uv run`).
- Pas de droits admin ni de compilateur nécessaires.

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
uv run waveaudit fiches <dossier-de-notes> [-o FICHIER] [--modele NOM] [--config FICHIER]
```

Traite les notes `.md`/`.txt` du dossier et produit un rapport Word de fiches de vulnérabilité
dans `var/sorties/<id-du-lot>/rapport.docx` (et, avec `-o`, une copie supplémentaire). `--modele`
choisit un modèle du manifeste (mode `local-gere`) ou surcharge le nom envoyé à l'API (mode
`externe`). `--config` ajoute un fichier TOML de configuration supplémentaire.

Autres commandes (`uv run waveaudit --help` pour le détail) :

| Commande | Rôle |
|---|---|
| `installer [--candidats]` | Télécharge et vérifie les artefacts du manifeste |
| `fiches DOSSIER [...]` | Lot CLI décrit ci-dessus |
| `incident DOSSIER [...]` | Analyse de journaux CERT décrite ci-dessous |
| `ui [--port N] [--config F]` | Démarre l'interface web locale |
| `banc DOSSIER [--modele NOM]` | Lot instrumenté (temps par fiche, pic mémoire) |
| `catalogue verifier [--config F]` | Contrôle le catalogue de constats types |
| `sbom` | Écrit le SBOM (CycloneDX) de l'environnement installé |
| `version` | Affiche la version installée |

## Utilisation — interface web

```
uv run waveaudit ui
```

Démarre une interface web strictement locale (`http://127.0.0.1:8765` par défaut, `--port` pour
changer). Elle n'accepte que les requêtes dont l'en-tête `Host` et `Origin` visent la boucle
locale. On y dépose un dossier de notes, on suit la progression du lot en direct, puis on
télécharge le rapport Word une fois le lot terminé.

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
est injoignable).

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
| Modèle de repli (RAM basse) | MiniCPM5 1B (GGUF Q4_K_M) | Apache-2.0 | huggingface.co/openbmb |
| Candidats (`--candidats`) | Qwen3 1.7B, Qwen3.5 0.8B (GGUF Q4_K_M) | Apache-2.0 | huggingface.co/unsloth |

Tous sous licence permissive. Le choix final entre candidats se fait hors nuit, avec
`slm-quality-bench`.

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

- Français uniquement, sortie Word, par lot (jamais en chat ni édition dans l'UI : la retouche se
  fait dans Word).
- Jamais de génération ex nihilo : toute fiche part d'un constat type du catalogue ; aucune
  référence absente du catalogue.
- Données publiques ou fictives seulement ; le bandeau « Démonstration — données fictives »
  figure sur toute sortie.
- Pas de chat interactif, pas d'assistant bureautique générique, pas de fine-tuning, pas de
  génération d'exploits, pas d'import des formats d'outils (Burp, Nessus), pas d'usage
  multi-utilisateur ni serveur.
- Toute donnée client réelle est hors périmètre.

## Contenu du dépôt

- `_bmad-output/forge/slm-edge-consultants-cyber/` : cadrage de l'idée (`forged-idea.md`) et rapport de la session (`forge-report.html`).
- `_bmad-output/specs/`, `_bmad-output/planning-artifacts/` : spécifications et architecture du POC.
- `_bmad/`, `.claude/skills/` : méthode [BMAD](https://github.com/bmad-code-org/BMAD-METHOD) pour la spécification et le développement.
- `.claude/cost-kit/` : contrôle rapide de [agent-cost-kit](https://github.com/Aliquanto3/agent-cost-kit).
- `theme-prive/` (ignoré par git, absent du dépôt public) : charte et logo Wavestone pour le
  thème du rapport Word ; le dépôt fonctionne sans lui (thème générique).

## Licence

[Apache 2.0](LICENSE).
