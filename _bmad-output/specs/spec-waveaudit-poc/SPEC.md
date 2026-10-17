---
id: SPEC-waveaudit-poc
companions:
  - formats.md
  - ../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/ARCHITECTURE-SPINE.md
  - ../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
sources:
  - ../../forge/slm-edge-consultants-cyber/forged-idea.md
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# WaveAudit — POC fiches de vulnérabilité hors ligne

## Why

**Mandat et douleur.** Les consultants du pool audit cyber de Wavestone ne peuvent soumettre aucune donnée client à un service d'IA externe (qualification PASSI, contrats, NDA), alors que la rédaction des fiches de vulnérabilité est répétitive. Leur poste (16 Go, CPU seul, 1,3 à 5,7 tok/s) n'admet qu'un traitement par lot, sans chat. Le produit est une application d'assistance à l'audit au moteur interchangeable : SLM local maintenant, LLM interne Wavestone cloisonné plus tard. Sa valeur durable tient aux workflows, au catalogue, au RAG et au gabarit, pas au modèle. Le POC, sur données publiques et fictives, doit convaincre 3 testeurs et un sponsor avant un pilote réel.

## Capabilities

- **CAP-1**
  - **intent:** Le consultant fournit un dossier de notes brutes (un fichier par constat) que l'outil lit en lot.
  - **success:** Les 20 notes de démonstration sont lues sans erreur. Une note vide ou mal formée est signalée dans le journal et le reste du lot est traité.
- **CAP-2**
  - **intent:** L'outil dispose d'un catalogue de constats types en français, rédigé à partir de sources publiques (CWE, OWASP WSTG, ANSSI).
  - **success:** Le catalogue compte au moins 30 entrées qui passent toutes la validation de schéma (`formats.md`). Chaque entrée a au moins une référence publique et un vecteur CVSS 3.1 par défaut valide.
- **CAP-3**
  - **intent:** Pour chaque note, l'outil retrouve dans le catalogue les constats types les plus proches, classés.
  - **success:** Sur les 20 notes de démonstration étiquetées, le constat attendu figure dans les 3 premiers candidats pour au moins 18 notes, et en première place pour au moins 15. La recherche se fait sans modèle de langage, de façon déterministe.
- **CAP-4**
  - **intent:** L'outil adapte le constat type retenu aux notes pour produire une fiche Description / Impact / Recommandation / CVSS 3.1 / Références.
  - **success:** Avec le faux moteur, chaque note donne une fiche complète. Si le moteur renvoie une sortie invalide, l'outil fait un seul nouvel essai, puis se replie sur le constat type marqué « à revoir ». Le lot ne s'arrête jamais sur une fiche.
- **CAP-5**
  - **intent:** Des garde-fous déterministes empêchent toute référence inventée et tout score CVSS incohérent.
  - **success:** Un test injecte par le faux moteur des références hors catalogue et un vecteur invalide. La fiche finale ne contient que des références du catalogue, chaque retrait est signalé, et le score est recalculé par le code depuis un vecteur validé, conforme aux exemples de la spécification FIRST.
- **CAP-6**
  - **intent:** L'outil produit un rapport Word : une fiche par constat, un bandeau « démonstration », un thème générique, ou le thème privé s'il est présent dans `theme-prive/`.
  - **success:** Le .docx produit se relit avec python-docx. Il contient le bandeau, une section par fiche avec les cinq rubriques, et le libellé « à revoir » là où il s'applique. Sans `theme-prive/`, l'export fonctionne avec le thème générique.
- **CAP-7**
  - **intent:** Le consultant lance le traitement d'un dossier de notes en ligne de commande et obtient le rapport.
  - **success:** Un test de bout en bout lance la CLI sur les 20 notes avec le faux moteur. Il obtient un .docx, un journal par fiche et un code retour 0. Un dossier absent ou un moteur injoignable donne un message clair et un code retour non nul.
- **CAP-8**
  - **intent:** Le consultant fait la même chose depuis une petite interface web locale : déposer les notes, lancer le lot, suivre l'avancement, télécharger le rapport.
  - **success:** Un test de bout en bout, en client HTTP avec le faux moteur, déroule le parcours jusqu'au téléchargement d'un .docx valide. Le serveur refuse d'écouter ailleurs que sur 127.0.0.1.
- **CAP-9**
  - **intent:** On change de moteur (endpoint, modèle, paramètres) par la seule configuration.
  - **success:** Le même lot, lancé sur deux faux endpoints configurés différemment, interroge l'endpoint choisi, sans changer le code.
- **CAP-10**
  - **intent:** L'installation récupère llama-server et les poids épinglés, vérifie leur empreinte et documente leur source.
  - **success:** Une empreinte SHA-256 incorrecte provoque un refus et la suppression du fichier. Le manifeste des artefacts (URL, version, licence, SHA-256) est versionné. Le test n'utilise pas le réseau (fichiers locaux simulés).
- **CAP-11**
  - **intent:** On peut prouver que l'outil ne fait aucun appel sortant à l'exécution et auditer ses dépendances.
  - **success:** Un test automatisé échoue dès qu'une connexion hors boucle locale est tentée pendant un lot CLI ou UI, et il passe sur le code livré. Une commande produit un SBOM (CycloneDX) des dépendances.
- **CAP-12**
  - **intent:** Un banc mesure le temps par fiche et le pic mémoire sur le vrai moteur.
  - **success:** La commande de banc produit un rapport (temps par fiche, pic RAM du moteur et de l'application). Avec le faux moteur, elle s'exécute en test rapide. Les seuils réels se vérifient hors nuit, sur l'EliteBook.

## Constraints

- Aucun appel réseau sortant à l'exécution (boucle locale seule) ; les téléchargements n'ont lieu qu'à l'installation.
- Données publiques ou fictives seulement ; le bandeau « démonstration » figure sur toute sortie.
- Jamais de génération ex nihilo : toute fiche part d'un constat type du catalogue.
- Cible : Windows 11, CPU seul, 16 Go avec Office ouvert, sans droits admin ni compilateur, Python 3.12 via uv. Pic mémoire total ≤ 6 Go ; moins de 3 min par fiche.
- Le moteur n'est appelé que par l'API compatible OpenAI. Aucun couplage au moteur local dans le code métier.
- La charte et le logo Wavestone restent hors du dépôt public (`theme-prive/`, ignoré par git) ; le dépôt fonctionne sans eux.
- Distribution par `git clone` + `uv sync`, avec des dépendances épinglées (`uv.lock`). L'installation complète prend moins de 10 min.
- Périmètre figé : notes vers fiche, en français, sortie Word, par lot (jamais en chat).
- Les tests automatisés n'utilisent ni le vrai modèle ni le réseau. Seul un test marqué `slow`, sauté si les poids sont absents, appelle le vrai moteur.
- L'architecture accueille un second workflow, CERT / réponse à incident (parseurs de logs, gabarit de rapport d'incident), sans refonte.

## Non-goals

- Chat interactif, assistant bureautique générique (mail, PPT, Excel).
- Fine-tuning d'un SLM (projet de R&D séparé) ; génération d'exploits.
- Fiches en anglais ; import des formats d'outils (Burp, Nessus).
- Développement du workflow CERT, du cas n°2 (scripts d'analyse) et des missions DR/défense.
- Édition des fiches dans l'UI (la retouche se fait dans Word) ; usage multi-utilisateur ou serveur.
- Toute donnée client réelle.

## Success signal

- Un collègue clone le dépôt et l'installe en moins de 10 min sur un EliteBook 16 Go. Il dépose 20 notes fictives et obtient un .docx de 20 fiches à moins de 3 min par fiche, avec 0 référence inventée et aucun appel sortant. Au moins 70 % des fiches sont jugées utilisables après retouches légères par 2 ou 3 collègues ; au moins 3 testeurs fournissent chacun un entrant, et un sponsor est identifié.

## Assumptions

- Notes : un fichier `.md` ou `.txt` par constat, avec un en-tête YAML optionnel et un corps libre (`formats.md`).
- Le catalogue est rédigé en propre dans le dépôt, sans copie de texte sous CC BY-SA, et cite les identifiants et URL publiques.
- Modèle par défaut : un SLM instruct de moins de 2B en GGUF Q4 sous licence permissive (par exemple Qwen3-1.7B, Apache 2.0, mode réflexion désactivé). Le choix final se fait hors nuit, avec `slm-quality-bench`.
- Les 20 notes de démonstration sont rédigées dans le dépôt, chacune étiquetée de son constat type attendu.
- La qualité perçue, la vitesse et la mémoire réelles se jugent hors nuit.

## Open Questions

- Entretien avec les collègues : frontière exacte (PASSI interne ou poste seul), poids réel des fiches, chaîne de rédaction et catalogue existant. Non bloquant pour le POC.
- Accès à PyPI, GitHub et Hugging Face depuis le poste ; faut-il une variante archive des poids ? Non bloquant pour la nuit.
- Accord de la communication pour la charte Wavestone. Non bloquant (thème hors dépôt).
