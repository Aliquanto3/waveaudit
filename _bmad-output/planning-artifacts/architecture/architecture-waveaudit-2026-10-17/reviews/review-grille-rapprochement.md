# Revue — grille du spine et rapprochement avec SPEC.md / formats.md

Fichier relu : `ARCHITECTURE-SPINE.md` (architecture-waveaudit-2026-10-17)
Entrées : `_bmad-output/specs/spec-waveaudit-poc/SPEC.md`, `formats.md`

## Verdict

Le spine couvre bien les 12 capacités et la plupart des contrats de `formats.md` avec des règles concrètes et codables sans deviner ; il reste exploitable pour une nuit de code autonome, mais quelques trous précis (bandeau hors docx, validation du catalogue, binds de AD-9) méritent une correction avant de lancer les stories.

## Mission A — Grille du spine

### A1. [Élevé] `AD-9` (garde réseau) a un champ `Binds` incomplet par rapport à sa propre règle et à la carte de capacités
- **Constat :** L'en-tête de AD-9 indique `Binds: CAP-11` uniquement. Mais la règle elle-même dit explicitement : « `securite/garde_reseau.activer(...)` est la première instruction des commandes `fiches`, `ui` et `banc` », ce qui concerne aussi CAP-7, CAP-8 et CAP-12. La table *Capability → Architecture Map* le confirme d'ailleurs pour CAP-8 (« Governed by AD-2, AD-9 ») sans que ce soit réciproque côté AD-9.
- **Risque pour la nuit :** un agent qui code la story CLI (CAP-7) ou banc (CAP-12) et ne lit AD-9 que via son `Binds` peut manquer l'obligation d'activer le garde réseau dans ces commandes, et ne découvrir l'incohérence qu'au test e2e `test_hors_ligne.py`.
- **Correction proposée :** mettre à jour `Binds` de AD-9 à `CAP-7, CAP-8, CAP-11, CAP-12`.

### A2. [Moyen] CAP-2 (catalogue) n'a pas de Rule d'AD dédiée pour ses critères de succès chiffrés
- **Constat :** CAP-2 exige « au moins 30 entrées », « chaque entrée a au moins une référence publique » et « un vecteur CVSS 3.1 par défaut valide ». La carte de capacités renvoie seulement vers « Conventions catalogue, `formats.md` » et la commande `waveaudit catalogue verifier` est citée dans le corps du document, mais aucune AD ne fixe l'algorithme de validation (vérifier `references` non vide, vérifier `cvss_vecteur` via `cvss.CVSS3`, compter les entrées ≥ 30, etc.).
- **Risque :** la story qui écrit le catalogue et celle qui écrit `catalogue verifier` peuvent diverger sur ce qui est réellement contrôlé (un agent pourrait ne valider que le schéma pydantic, pas les deux règles métier additionnelles du CAP-2).
- **Correction proposée :** ajouter une Rule courte (ou étendre AD-1/créer AD-16) : *« `waveaudit catalogue verifier` charge chaque fichier `donnees/catalogue/<famille>.yaml`, valide le schéma `ConstatType`, vérifie `len(references) >= 1` et que `cvss_vecteur` est accepté par `cvss.CVSS3`, et échoue si le total des constats < 30. »*

### A3. [Moyen] Le périmètre du regex anti-référence-inventée (AD-5) ne couvre pas les identifiants ANSSI/CERT-FR
- **Constat :** `formats.md` cite explicitement « guide ANSSI » comme type de référence du catalogue, mais la liste de motifs de AD-5 (`CWE-\d+`, `CVE-\d{4}-\d+`, `CAPEC-\d+`, `WSTG-[A-Z]+-\d+`, `A\d{2}:20\d{2}`, URL) ne reconnaît aucun identifiant ANSSI/CERT-FR textuel (ex. `CERTFR-2023-ALE-001`, `ANSSI-BP-028`) qui ne serait pas une URL.
- **Risque :** si le faux moteur ou le vrai modèle insère une mention ANSSI inventée dans le corps d'une rubrique sans URL, elle n'est pas détectée ni retirée par l'étape 2 de AD-5, ce qui affaiblit la garantie « 0 référence inventée » de CAP-5 pour ce type précis de référence (notons que le champ `Références` officiel de la fiche reste, lui, toujours recopié du catalogue — seul le texte libre est concerné).
- **Correction proposée :** ajouter un motif (par ex. `(?:CERTFR|ANSSI)-[A-Z0-9-]+`) à la liste de AD-5, ou documenter que les références ANSSI du catalogue sont toujours exprimées par leur URL (et donc déjà couvertes par le motif URL) — à trancher explicitement plutôt que de laisser l'agent le découvrir.

### A4. [Faible] AD-6 ne liste pas CAP-8 dans ses `Binds`
- **Constat :** AD-6 (repli et continuité du lot) est bindée à CAP-1, CAP-4, CAP-7. Or le service de lot est unique pour CLI et UI (AD-2), donc CAP-8 bénéficie des mêmes règles de repli/continuité. Ce n'est pas un vrai point de divergence (AD-2 garantit l'unicité), mais la carte de traçabilité est incomplète.
- **Correction proposée :** ajouter CAP-8 aux `Binds` de AD-6 pour que la carte reflète la réalité du code partagé.

### A5. [Faible] Formulation CAP-8 vs règle UI sur l'adresse d'écoute
- **Constat :** CAP-8 dit « Le serveur refuse d'écouter ailleurs que sur 127.0.0.1 » ; le corps du spine dit « Le serveur web refuse de démarrer si `ui.hote` n'est pas une adresse de boucle locale » (ce qui autorise aussi `::1` / `localhost`). Léger écart de formulation entre l'exigence (127.0.0.1 strict) et la règle (boucle locale au sens large).
- **Correction proposée :** aligner explicitement — soit restreindre la règle à `127.0.0.1` par défaut, soit préciser dans le CAP/la spec que « boucle locale » est l'intention réelle, pour que le test e2e sache quoi vérifier.

Le reste de la grille est solide : les 12 capacités sont toutes bindées (frontmatre + table de capacités), les AD-1 à AD-15 sont concrètes et codables sans ambiguïté majeure (BM25 avec k1/b fixés, regex de garde-fous, codes retour, statuts, schéma de sortie modèle), le bloc *Deferred* ne laisse filer aucune divergence inter-stories (les valeurs par défaut sont fixées dans la Stack/Structural Seed, seul le choix final est repoussé), et déploiement/environnements/exploitation (distribution git+uv, cible Windows, logging, SBOM, codes retour) sont chacun soit décidés soit explicitement différés.

## Mission B — Rapprochement SPEC.md / formats.md → spine

### B1. [Élevé] Constraint « le bandeau « démonstration » figure sur toute sortie » n'est opérationnalisé que pour le .docx
- **Constat :** La contrainte de SPEC.md est générale (« toute sortie »), mais AD-14 (seule AD qui traite le bandeau) ne couvre que l'export Word (en-tête/pied de page). Rien dans AD-8/AD-9/routes UI n'exige d'afficher le bandeau « Démonstration — données fictives » sur les pages web (`GET /`, `GET /lots/{id}`) ni dans la sortie CLI.
- **Correction proposée :** soit restreindre explicitement la contrainte au seul artefact exportable (rapport .docx) dans une note de clarification du spine, soit étendre AD-14 (ou une nouvelle petite règle sous la section UI) pour exiger le bandeau dans les gabarits `interfaces/web/templates/` également. À trancher avant la nuit pour éviter qu'un agent choisisse arbitrairement.

### B2. [Moyen] `formats.md` — champ `severite_pressentie` de la note : destination non précisée
- **Constat :** Le champ est documenté comme optionnel côté entrée, mais aucune AD ni section du spine ne dit s'il est ignoré, affiché en traçabilité, ou utilisé ailleurs. Rien ne le contredit, mais rien ne confirme explicitement qu'il est volontairement inerte (à la différence de `constat_attendu`, dont `formats.md` dit lui-même « ignoré par le traitement »).
- **Correction proposée :** une ligne dans les conventions ou dans la map CAP-1 précisant que `severite_pressentie` est un champ d'information consultant, non consommé par le pipeline du POC — pour éviter qu'un agent essaie de le câbler dans la recherche ou la fiche sans le demander.

### B3. [Faible] Reste du rapprochement : cohérent
- **Constat :** toutes les autres exigences chiffrées (CAP-1 à CAP-12, seuils de CAP-3, schéma `SortieModele` d'AD-4 vs `formats.md` Fiche, poids BM25 d'AD-7 vs champs indexés de `formats.md` Constat type, codes retour, statuts `ok/a_revoir/non_traitee/non_rattachee`, manifeste d'artefacts vs CAP-10, SBOM vs CAP-11, non-goals — chat, édition UI, anglais, Burp/Nessus, CERT) atterrissent correctement dans le spine, sans contradiction relevée.

## Fichier de revue

`C:\Users\anael.yahi\Documents\GitHub\waveaudit\_bmad-output\planning-artifacts\architecture\architecture-waveaudit-2026-10-17\reviews\review-grille-rapprochement.md`
