---
id: SPEC-waveaudit-cert
companions:
  - formats-incident.md
  - ../spec-waveaudit-poc/SPEC.md
  - ../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/ARCHITECTURE-SPINE.md
  - ../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
sources: []
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# WaveAudit — workflow CERT / réponse à incident

## Why

**Opportunité.** Une mission de réponse à incident se déroule sur un réseau client compromis, où le hors-ligne est imposé et où un service d'IA externe est hors de question. La première journée se passe à trier des journaux pour reconstituer une chronologie et à rédiger un rapport d'incident. Cette extension n°2, prévue dès le cadrage, réutilise le moteur et les garanties du POC (hors ligne, rien d'inventé, SLM local) sur une autre tâche répétitive. Elle doit démontrer que la plateforme sert plusieurs métiers de Wavestone.

## Capabilities

- **CAP-1**
  - **intent:** L'analyste fournit un dossier de journaux exportés (Windows Security et Sysmon en CSV ou JSON ; Linux `auth.log`, `syslog` ou `secure`) que l'outil normalise en événements horodatés.
  - **success:** Le jeu de démonstration est entièrement lu : les lignes ignorées sont exactement celles de l'oracle (`ignorees`). Chaque ligne illisible est comptée et signalée, sans arrêter l'analyse. Les horodatages sont tous avec fuseau, et l'origine de chaque événement (fichier et ligne) est conservée.
- **CAP-2**
  - **intent:** Un catalogue de règles de détection en YAML décrit les faits suspects (force brute, compte créé, ajout à un groupe d'administrateurs, PowerShell encodé, journal effacé, etc.), chacune avec un texte type et des références MITRE ATT&CK.
  - **success:** Le catalogue contient les 15 règles du catalogue minimal, avec les conditions normatives de `formats-incident.md`, et passe `verifier_regles`. Chacune a au moins une référence ATT&CK et un test qui la déclenche.
- **CAP-3**
  - **intent:** Le moteur de détection applique les règles aux événements, de façon déterministe, avec des seuils et des fenêtres de temps.
  - **success:** Sur le jeu de démonstration, la liste des détections est égale à celle de l'oracle `donnees/demo/incident-attendu.yaml` (16 détections, ni manquante ni en trop), la part d'événements bénins est d'au moins 60 %, et deux exécutions donnent un `incident.json` identique.
- **CAP-4**
  - **intent:** Le code extrait les indicateurs de compromission (IP, comptes, hôtes, hachages, exécutables) et les actifs touchés à partir des événements détectés.
  - **success:** Sur le jeu de démonstration, la liste des indicateurs (type, valeur, origines) est égale à celle de l'oracle. Chaque indicateur renvoie à au moins un événement source.
- **CAP-5**
  - **intent:** Le SLM adapte le texte type de chaque détection en un récit tiré des preuves, et des garde-fous retirent tout indicateur ou toute référence absents des preuves et de la règle.
  - **success:** Avec le faux moteur, chaque détection donne un récit. Le scénario `references_inventees` injecte une IP, un hachage et une technique ATT&CK inventés : tous sont retirés et signalés, sans mutiler horodatages ni numéros de version. En cas d'échec du moteur, le récit reprend le texte type avec le statut « à revoir ».
- **CAP-6**
  - **intent:** L'outil produit un rapport d'incident Word : synthèse, chronologie, faits détectés avec leurs preuves, indicateurs, actifs touchés, recommandations et bandeau « démonstration ».
  - **success:** Le .docx produit se relit avec python-docx. Il contient toutes les sections dans l'ordre, une ligne de chronologie par détection, et le tableau des indicateurs identique à l'extraction.
- **CAP-7**
  - **intent:** L'analyste lance l'analyse en ligne de commande sur un dossier de journaux.
  - **success:** Un test de bout en bout de `waveaudit incident <dossier>` avec le faux moteur donne le code 0 et un rapport, sans aucun appel sortant. Un dossier vide ou absent donne le code 2. Moteur injoignable : code 3 sur la démo, code 0 sur un dossier sans détection (le moteur n'est pas ouvert).

## Constraints

- Toutes les contraintes de SPEC-waveaudit-poc s'appliquent : hors ligne, données fictives, SLM < 2B, moteur interchangeable, Windows sans admin, traitement par lot.
- Le SLM ne décide jamais de ce qui est suspect : la détection, les indicateurs et la chronologie sont déterministes.
- Toute affirmation du rapport (indicateur, horodatage, hôte) renvoie à une ligne source.
- Aucune dépendance nouvelle sans licence permissive vérifiée ; on n'ajoute pas de parseur EVTX.

## Non-goals

- Fichiers EVTX binaires, journaux web, flux réseau (PCAP), mémoire.
- Interface web pour le CERT (CLI seulement dans cette version).
- Corrélation avancée entre sources, enrichissement en ligne (réputation IP, VirusTotal), règles Sigma importées telles quelles.
- Remédiation automatique.

## Success signal

- Sur le scénario de démonstration, une compromission fictive qui commence par une force brute SSH et se termine par l'effacement des journaux Windows, `waveaudit incident` produit un rapport qui reconstitue la chronologie complète (17 étapes, 16 détections). Tous les indicateurs sont exacts et sourcés, et rien n'est inventé. Avec le faux moteur, le test e2e de la démo dure moins de 30 s ; la durée avec le vrai SLM est mesurée hors CI.

## Assumptions

- Les exports Windows suivent le format normalisé de `formats-incident.md`, produit par le script PowerShell fourni dans le README (`ConvertTo-Json` brut de PowerShell 5.1 ne suffit pas).
- Les horodatages syslog RFC 3164 n'ont ni année ni fuseau : l'année est donnée par `--annee` (par défaut l'année en cours) et le décalage, fixe et sans heure d'été, par la configuration. Un incident à cheval sur un changement d'heure demande deux analyses.
- Le jeu de démonstration (journaux fictifs) et son oracle `donnees/demo/incident-attendu.yaml`, rangé hors du dossier lu et calculé à la main, sont rédigés dans le dépôt. Les textes types et la qualité du récit réel relèvent d'une revue humaine.
