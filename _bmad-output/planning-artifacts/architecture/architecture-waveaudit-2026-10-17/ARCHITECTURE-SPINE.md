---
name: 'WaveAudit'
type: architecture-spine
purpose: build-substrate
altitude: feature
paradigm: 'hexagonal (ports et adaptateurs) avec un noyau de workflow en pipeline (pipes-and-filters)'
scope: 'WaveAudit : notes brutes vers fiches de vulnérabilité et journaux vers rapport d''incident, hors ligne, CLI + UI locale ; v2 : qualité, relecture dans l''UI, anglais, incident dans l''UI'
status: final
created: '2026-10-17'
updated: '2026-10-18'
binds: [POC CAP-1 à CAP-12, CERT CAP-1 à CAP-7, V2 CAP-1 à CAP-17]
sources:
  - ../../../specs/spec-waveaudit-poc/SPEC.md
  - ../../../specs/spec-waveaudit-cert/SPEC.md
  - ../../../specs/spec-waveaudit-v2/SPEC.md
  - ../../ux/EXPERIENCE.md
companions:
  - contrats.md
  - impacts-v2.md
  - ../../../specs/spec-waveaudit-v2/formats.md
  - ../../../specs/spec-waveaudit-poc/formats.md
---

# Architecture Spine — WaveAudit (POC, CERT, v2)

## Design Paradigm

Hexagonal. Le **domaine** (modèles, règles pures) et les **workflows** (pipeline par élément) ne connaissent que des **ports** (`typing.Protocol`). Les **adaptateurs** (moteur HTTP, llama-server, catalogue YAML, notes sur disque, export Word) implémentent ces ports. Une seule **racine de composition** les assemble. Les **interfaces** (CLI, web) n'appellent que le service de lot de l'**application**.

Workflow `fiches` = pipeline par note : `lire → rechercher → adapter → controler`, puis `assembler` sur le lot. Le workflow CERT a son propre service derrière les mêmes ports (AD-17). La v2 ajoute un état de relecture persistant par lot (AD-19), servi à l'UI par une API locale (AD-22).

```mermaid
flowchart TD
  interfaces["interfaces/ (cli, web)"] --> application["application/ (lot, incident, composition, relecture, moteur_demande, lots, export)"]
  application --> workflows["workflows/ (fiches, incident, registre)"]
  application --> adaptateurs["adaptateurs/"]
  workflows --> domaine["domaine/ (modèles, règles, ports, relecture, qualite_texte)"]
  adaptateurs --> domaine
  securite["securite/ (garde réseau)"] -.activé par.- interfaces
  installation["installation/ (manifeste, SHA-256, SBOM)"] --> domaine
```

## Invariants & Rules

Les formes exactes (modèles, ports, configuration, manifeste, signatures) sont dans `contrats.md`, annexe normative : les § cités ci-dessous y renvoient.

### AD-0 — Socle commun livré seul et en premier

- **Binds:** all
- **Prevents:** des fichiers partagés (`pyproject.toml`, `uv.lock`, `conftest.py`, modèles, ports, configuration) réécrits de façon incompatible par des stories parallèles.
- **Rule:**
  - La story `socle` est exécutée, intégrée et vérifiée (suite verte sur `main`) avant toute autre. Elle crée :
    - `pyproject.toml` (toutes les dépendances de la table Stack, épinglées ; `addopts = "-m 'not slow' --allow-hosts=127.0.0.1,::1"` ; ruff) et `uv.lock` ;
    - l'arborescence avec les `__init__.py` ;
    - `domaine/modeles.py`, `ports.py`, `erreurs.py` et `configuration.py` ;
    - `application/config.py` ;
    - `config/waveaudit.toml` et `config/artefacts.toml` ;
    - `workflows/registre.py` (protocole) ;
    - `tests/conftest.py`, `tests/faux_moteur.py` et `tests/unitaires/test_architecture.py`.
  - Les stories suivantes ne modifient pas ces fichiers. Un manque (champ, dépendance, fixture) s'arrête et se signale.
  - Elles ajoutent leurs propres modules, et leurs tests sous `tests/unitaires/test_<module>.py` ou `tests/e2e/test_<sujet>.py`.
  - **[v2]** Fichiers du socle touchés par la v2, tous par la seule story de socle v2 (AD-18) :
    - `domaine/modeles.py` (§1 v2) ;
    - `domaine/configuration.py` et `config/waveaudit.toml` (§2 v2) ;
    - `domaine/ports.py` (§3 : `seed`, `OptionsExport`) ;
    - `config/artefacts.toml` (§11 : rôles, champs facultatifs, avec `installation/manifeste.py`) ;
    - `tests/faux_moteur.py` (§13 v2) ;
    - `tests/unitaires/test_architecture.py` (règle des noms privés de `lot.py`).

    Aucune nouvelle dépendance : `pyproject.toml` et `uv.lock` ne changent pas. `tests/conftest.py`, `domaine/erreurs.py`, `application/config.py` et `workflows/registre.py` ne changent pas. Les aides de test web vont dans `tests/web_outils.py`.

### AD-1 — Sens des dépendances

- **Binds:** all
- **Prevents:** du HTTP, du YAML ou du docx glissé dans la logique métier, qui rendrait le moteur non interchangeable et les tests dépendants du réseau.
- **Rule:**
  - Le sens suit le diagramme : `domaine/` et `workflows/` n'importent que la stdlib, `pydantic` et `domaine`. Exception : `domaine/cvss31.py`, seul importateur de `cvss`.
  - Imports réservés (analyse limitée à `src/waveaudit/`) :
    - `httpx` : `adaptateurs/` et `installation/telechargement.py` ;
    - `psutil`, `yaml`, `docx` : `adaptateurs/` ;
    - `fastapi`, `jinja2`, `multipart` : `interfaces/web/` ;
    - `uvicorn`, `typer` : `interfaces/cli.py`.
  - `installation` est importé seulement par `application/` et `interfaces/cli.py`.
  - Seul `application/composition.py` instancie des adaptateurs. **[v2]** Il expose aussi `creer_exporteur`, `creer_catalogue`, `modeles_installes` et `journal_reconnu` : l'UI et le banc n'atteignent les adaptateurs et le manifeste que par là.
  - **[v2]** `domaine/relecture.py` et `domaine/qualite_texte.py` relèvent de la règle du domaine (stdlib, `pydantic`, `domaine`). `interfaces/web/` importe `application/` et `domaine/`, jamais `installation`, `adaptateurs` ni `workflows`. La régénération passe par `application/relecture.py`, seul module applicatif hors `lot.py` qui importe `workflows.fiches`.
  - `tests/unitaires/test_architecture.py` (analyse des `import` par `ast`) fait respecter ces règles ; `tests/` n'y est pas soumis, sauf pour la règle v2 des noms privés de `lot.py` (AD-18).

### AD-2 — Un seul service de lot pour la CLI et l'UI [ADOPTED]

- **Binds:** CAP-7, CAP-8, CAP-12
- **Prevents:** deux implémentations du pipeline qui divergent entre la CLI et l'UI, ou des identifiants de lot différents.
- **Rule:**
  - Point d'entrée unique : `application.lot.executer_lot(requete: RequeteLot, config: Configuration, abonne) -> ResultatLot` (contrats §1, §9).
  - La CLI l'appelle directement. L'UI l'exécute dans un thread, un lot à la fois (HTTP 409 sinon). **[v2]** « Un à la fois » couvre lot de fiches, incident et régénération (AD-20).
  - `id_lot` vient de `nouvel_id_lot` et sert partout (`var/entrees/`, `var/sorties/`, routes).
  - L'avancement passe exclusivement par `EvenementLot`.

### AD-3 — Port moteur et adaptateur compatible OpenAI [ADOPTED]

- **Binds:** CAP-4, CAP-9
- **Prevents:** un couplage au moteur local, des formats de requête différents, ou une classification d'erreurs divergente.
- **Rule:**
  - Port `Moteur`, avec `sonder()` et `generer_json(...)` (contrats §3). Seul `adaptateurs/moteur_openai.py` fait ces appels HTTP.
  - `base_url` se termine toujours par `/v1` et utilise `127.0.0.1`, jamais `localhost`.
  - `httpx.Client(trust_env=False)` : le proxy d'entreprise est ignoré à l'exécution.
  - `SortieInvalide` est levée seulement pour un contenu non JSON ou qui n'est pas un objet. `MoteurInjoignable` est levée pour une connexion refusée, un timeout ou un statut différent de 200.
  - L'adaptateur ne valide pas le schéma.
  - **[v2]** Le port porte `seed` facultatif (contrats §3) ; `repeat_penalty` et `reflexion` sont des réglages de l'adaptateur, venus du manifeste ou de la configuration, jamais du workflow.

### AD-4 — Contrat de sortie du modèle [ADOPTED]

- **Binds:** CAP-4, CAP-5
- **Prevents:** qu'un SLM de moins de 2B invente des références, un format ou un vecteur.
- **Rule:**
  - Un appel par fiche, avec `response_format` json_schema = `schema_sortie(longueur_max_rubrique)` (contrats §1) : 4 rubriques et métriques CVSS en enums. Aucun champ de références.
  - Le prompt suit contrats §8 : balises `<constat>` et `<note>` dans le dernier message `user`, corps tronqué à `taille_max_note`.
  - Le préfixe système propre au modèle (`/no_think` pour Qwen3) arrive par `Ports.prefixe_systeme`.
  - **[v2]** Les balises `note`/`constat` présentes dans la note sont neutralisées (`<` → `‹`, même longueur). La consigne et les textes du constat suivent la langue du lot (contrats §8, AD-21).

### AD-5 — Garde-fous déterministes après le modèle

- **Binds:** CAP-5
- **Prevents:** une référence inventée, un score incohérent ou une rubrique vide dans la fiche finale.
- **Rule:** `domaine/garde_fous.appliquer` s'applique à chaque fiche, repli compris, dans l'ordre de contrats §6 :
  1. références copiées du constat type ;
  2. retrait des jetons de type référence hors constat (insensible à la casse, motifs CWE, CVE, CAPEC, WSTG, OWASP, ANSSI, CERT-FR et URL) ;
  3. métriques invalides → vecteur par défaut ;
  4. rubrique trop courte → texte du constat type.
  - Score et sévérité viennent uniquement de `domaine/cvss31.evaluer`.
  - `statut = a_revoir` si et seulement si `motifs` n'est pas vide.
  - **[v2]** Ordre révisé (contrats §6 v2) :
    - seuils titre 5 / rubriques 20 ;
    - URL citée par la note conservée ;
    - puis répétition et langue (`domaine/qualite_texte`, partagé avec les récits d'incident). Ces deux garde-fous signalent sans réécrire le texte.

    Algorithmes et seuils mesurés sur 17 lots réels : contrats §6.
  - **Touche :** `domaine/garde_fous.py`, `domaine/garde_fous_incident.py`, `domaine/qualite_texte.py` ; tests `test_garde_fous.py`, `test_garde_fous_incident.py`, `test_qualite_texte.py`, `test_pipeline*.py`.

### AD-6 — Repli et continuité du lot

- **Binds:** CAP-1, CAP-4, CAP-7
- **Prevents:** un lot interrompu par une seule note, ou des comportements d'erreur différents selon l'interface.
- **Rule:**
  - `SortieInvalide`, y compris une rubrique absente vue par le workflow, déclenche un seul nouvel essai, puis le repli `repli_sortie_invalide`. **[v2]** Le nouvel essai passe `seed = moteur.seed + 1`, en fiches comme en incident (contrats §5).
  - `MoteurInjoignable` en cours de lot déclenche un repli immédiat (`repli_moteur`). Le repli reprend le constat type, avec le statut `a_revoir`.
  - Une note invalide donne une `EntreeEcartee` `non_traitee`.
  - Score BM25 maximal `<= 0` : `EntreeEcartee` `non_rattachee`, sans appel au modèle (pas de génération ex nihilo).
  - Seules la sonde initiale en échec, une entrée ou une configuration invalide, et `ConnexionInterdite` arrêtent le lot.

### AD-7 — Recherche lexicale déterministe

- **Binds:** CAP-3
- **Prevents:** une dépendance à un modèle d'embedding, ou plusieurs classements concurrents.
- **Rule:**
  - `domaine/recherche.classer`, BM25 sans dépendance externe, avec la tokenisation, la pondération par répétition des champs et l'IDF positif de contrats §7.
  - La requête n'inclut jamais `constat_attendu` ni `actif`.
  - Le constat retenu est le premier candidat ; les 3 premiers vont dans `Tracabilite.candidats`.
  - **[v2]** Un seul index bilingue (textes fr et `en` du constat dans le même document), quelle que soit la langue du lot. Le réglage CAP-5 se fait sur cet index ; `test_rattachement_demo.py` devient bloquant (contrats §7, §29).

### AD-8 — Résultats d'un lot et événements

- **Binds:** CAP-6, CAP-7, CAP-8, CAP-12
- **Prevents:** un export qui relit autre chose que le rapport validé, ou plusieurs écrivains du journal.
- **Rule:**
  - Chaque lot écrit dans `var/sorties/<id_lot>/` : `fiches.json` (= `Rapport`), `journal.jsonl` et `rapport.docx`.
  - `application/lot.py` est le seul émetteur d'`EvenementLot` et le seul écrivain de `journal.jsonl` ; il écrit avant d'appeler l'abonné.
  - L'exporteur ne lit qu'un `Rapport`. **[v2]** Exports final et brouillon : un `Rapport` dérivé de `relecture.json` par `domaine/relecture.rapport_export`, plus `OptionsExport` (contrats §27).
  - **[v2]** Fichiers d'un lot : liste fermée (contrats §30). Écrivains uniques :
    - `journal.jsonl` → `JournalLot` ;
    - `relecture.json` → `application/relecture.py` (AD-19) ;
    - `lot.json` → le service du lot.

    L'état d'un lot affiché par l'UI se lit sur le disque (`application/lots.py`), jamais dans un registre en mémoire.
  - Éléments triés par nom de note (`casefold`) ; noms de fichiers seulement, jamais de chemin absolu, dans la traçabilité et le journal.

### AD-9 — Hors ligne vérifiable

- **Binds:** CAP-7, CAP-8, CAP-11, CAP-12
- **Prevents:** un appel sortant introduit par une dépendance (télémétrie, CDN, proxy) sans que rien le détecte.
- **Rule:**
  - API `securite/garde_reseau` (contrats §12). Les commandes `fiches`, `ui` et `banc` chargent la configuration, puis exécutent tout le reste dans `with garde(config.reseau.hotes_autorises)`.
  - `ConnexionInterdite` n'hérite pas d'`OSError`, n'est jamais convertie et donne le code 4.
  - Seule la commande `installer` s'exécute sans garde.
  - Côté tests : pytest-socket `--allow-hosts=127.0.0.1,::1`, jamais `--disable-socket`. `tests/e2e/test_hors_ligne.py` exécute un lot CLI et un lot UI (`TestClient`) sous `garde(...)` et exige `tentatives() == []`.
  - Aucune URL externe dans les gabarits ni dans les fichiers statiques (test dédié).

### AD-10 — Faux moteur de test [ADOPTED]

- **Binds:** CAP-4, CAP-5, CAP-7, CAP-8, CAP-9, CAP-11, CAP-12
- **Prevents:** des tests qui exigent un vrai modèle, ou un bouchon inventé par chaque story.
- **Rule:**
  - Un seul faux moteur, `tests/faux_moteur.py`, exposé par la fixture **fabrique** `faux_moteur(scenario)`, avec ses scénarios et la fixture `config_test` (contrats §13).
  - Aucun test n'écrit dans le `var/` du dépôt.
  - Seuls les tests marqués `slow` lancent le vrai llama-server ; ils sont sautés si les poids sont absents.

### AD-11 — Cycle de vie de llama-server [ADOPTED]

- **Binds:** CAP-9, CAP-10, CAP-12
- **Prevents:** des processus orphelins, une écoute réseau hors boucle locale, ou deux propriétaires du moteur.
- **Rule:**
  - Seul `application/composition.ouvrir` démarre le moteur (contrats §9), une fois par lot, CLI et UI comprises. `pid_moteur` est publié dans `lot_demarre`.
  - `adaptateurs/llama_server.LlamaServer` (contrats §10) :
    - écoute sur `127.0.0.1` et un port libre ;
    - reçoit toujours `-c` et `-t` explicitement (sans contexte borné, le cache KV fait exploser la RAM) ;
    - est rattaché à un Job Object `KILL_ON_JOB_CLOSE` par `OpenProcess` ;
    - écrit sa sortie dans `var/journaux/`, jamais dans un tube non lu.
  - Le modèle de repli est choisi si la RAM disponible est sous `ram_min_defaut_go`.
  - **[v2]** `composition.ouvrir` reste le seul démarreur. Il est appelé par le lot, par l'incident et par `MoteurALaDemande` (AD-20), jamais deux à la fois.

### AD-12 — Manifeste des artefacts et installation

- **Binds:** CAP-10, CAP-11
- **Prevents:** des poids ou un binaire non vérifiés, ou des chemins codés en dur.
- **Rule:**
  - `config/artefacts.toml` est un tableau `[[artefact]]` (contrats §11). Rôles :
    - `moteur` : llama-server b11714 ;
    - `modele_defaut` : granite-4.0-1b ;
    - `modele_repli` : Qwen3.5-0.8B (**[v2]**, `reflexion = false`) ;
    - `candidat` : Qwen3-1.7B (`/no_think`), MiniCPM5-1B (**[v2]**, gardé pour le banc).
    - **[v2]** Permutation granite / qwen3-1.7b seulement par la story de rebanc, sur les seuils de CAP-7 (contrats §11).
  - `waveaudit installer` installe le moteur, le défaut et le repli ; `--candidats` ajoute les candidats. Les fichiers passent par `.part`, puis sont vérifiés (taille et SHA-256) et renommés. En cas d'écart : suppression et code 5.
  - Les tests utilisent `httpx.MockTransport`.
  - Les chemins ne s'obtiennent que par `installation.manifeste`.
  - `waveaudit sbom` écrit `var/sbom.cdx.json` en analysant l'interpréteur du venv.

### AD-13 — Configuration

- **Binds:** all
- **Prevents:** des réglages lus à plusieurs endroits, ou des clés et défauts qui divergent.
- **Rule:**
  - Clés, types et défauts exacts : contrats §2, avec `extra="forbid"`.
  - Le modèle est dans `domaine/configuration.py`, le chargement dans `application/config.py` (`charger_configuration`, `racine_projet`).
  - Surcharge par `waveaudit.local.toml` (ignoré par git) puis par `--config`.
  - Aucun `os.environ` ni lecture de configuration ailleurs.
  - Chemins relatifs résolus contre `racine_projet()`, jamais contre `cwd`.

### AD-14 — Thème et bandeau

- **Binds:** CAP-6, CAP-7, CAP-8
- **Prevents:** une charte Wavestone qui fuit dans le dépôt, un export qui échoue sans elle, ou une sortie sans bandeau.
- **Rule:**
  - Le rapport Word suit contrats §17 : intitulés exacts, bandeau en en-tête et en pied, annexe des entrées écartées. Il utilise `theme-prive/` s'il existe, le thème générique sinon. **[v2]** Libellés par langue : contrats §27.
  - **[v2, révisé]** La palette Wavestone est publique, versionnée dans `interfaces/web/static/tokens.css` (contrats §28). Seul le logo reste privé : `theme-prive/web/logo.svg`, servi par `/theme/logo.svg` s'il existe, sans erreur s'il manque. La charte Word (`modele.docx`, `theme.toml`) reste dans `theme-prive/`.
  - Le bandeau exact `Démonstration — données fictives` figure aussi sur chaque page web (en haut et en bas, non masquable) et en première et dernière ligne de la sortie CLI de `fiches`, `incident` et **[v2]** `exporter`. Le Word d'un lot `en` porte `Demonstration — fictitious data`.
  - **Touche :** `adaptateurs/export_docx.py`, `interfaces/web/static/`, `interfaces/web/templates/`, `interfaces/web/app.py` ; tests `test_export_docx.py`, `test_ui.py`.

### AD-15 — Extension par workflow

- **Binds:** CAP-7 (et le futur workflow CERT)
- **Prevents:** une refonte au moment d'ajouter le workflow de réponse à incident, ou un workflow qui contourne AD-1.
- **Rule:**
  - `workflows/registre.REGISTRE` associe un nom à une fabrique `(Configuration, Ports) -> Workflow` (contrats §5). Le workflow reçoit ses ports et n'instancie rien.
  - `traiter` ne fait aucune entrée-sortie et n'émet aucun événement.
  - Seul `fiches` est enregistré. Un workflow vit dans `workflows/<nom>/` sans dépendre d'un autre.

### AD-16 — Formes partagées figées

- **Binds:** CAP-1 à CAP-12
- **Prevents:** deux stories qui codent `Fiche`, `EvenementLot`, `Configuration` ou un port avec des champs différents, ou des identifiants de constat inventés séparément pour le catalogue et pour les notes (CAP-3 tomberait à 0).
- **Rule:**
  - Les modèles, ports, erreurs, codes retour, format de manifeste, faux moteur, API web et CLI sont ceux de `contrats.md`. Les identifiants de constat et de notes sont ceux de contrats §16.
  - Toute divergence nécessaire passe par une mise à jour de `contrats.md` dans une story dédiée, jamais par une variante locale.
  - **[v2]** S'y ajoutent les formes v2 : `TextesConstat`, `Langue`, `OptionsExport`, `EtatRelecture` et ses entrées, `Occupation`, `ResumeLot`, `ModeleInstalle`, les codes d'erreur de l'API (contrats §26) et le schéma YAML bilingue (contrats §15).

### AD-17 — Workflow incident (CERT), service dédié

- **Binds:** SPEC-waveaudit-cert CAP-1 à CAP-7
- **Prevents:** une généralisation forcée du protocole `Workflow` des fiches ; un second moteur, garde réseau, écrivain de journal ou format d'événements ; des stories parallèles qui se rencontrent sans contrat figé.
- **Rule:**
  - Le CERT a ses propres formes, ports et service (contrats §21) : `domaine/incident.py`, `workflows/incident/` et `application/incident.executer_incident`. Il n'est pas inscrit dans `REGISTRE`.
  - Il réutilise sans les dupliquer : le port `Moteur`, la composition, le garde réseau, `EvenementLot` (sans nouveau `TypeEvenement`), `nouvel_id_lot` et les conventions.
  - Seule la story C1 modifie le code existant du MVP : ajouts aux fichiers AD-0 (formes, ports, configuration, faux moteur) et deux extractions sans changement de comportement, `application/journal.JournalLot` (tiré de `lot.py` ; il devient l'unique écrivain de `journal.jsonl` au sens d'AD-8) et `composition.ouvrir_moteur_incident` (tiré d'`ouvrir`). Les autres stories CERT n'ajoutent que des fonctions ou une commande nouvelles (`creer_ports_incident`, commande `incident`).
  - La création des ports (`creer_ports_incident`, sans processus) est séparée de l'ouverture du moteur, ouvert seulement s'il y a au moins une détection.
  - Conditions des règles, champs normalisés, chronologie de démo et schéma de l'oracle sont normatifs dans `formats-incident.md`. C1 les traduit en constantes (`domaine/incident.py`) et en fixture (`tests/donnees/incident/canoniques.yaml`) : c'est là que C2, C3 et C4 se rencontrent.
  - L'oracle `donnees/demo/incident-attendu.yaml` est hors du dossier lu et ne se régénère jamais depuis une sortie du programme.
  - La détection, les indicateurs et la chronologie sont déterministes ; le SLM ne rédige que le récit.

### AD-18 — Socle v2 livré seul et en premier

- **Binds:** SPEC-waveaudit-v2 (toutes les CAP), CAP-1 et CAP-16 en propre
- **Prevents:** des stories v2 parallèles qui ajoutent chacune leur champ à `ConstatType`, leur code à `CodeMotif`, leur clé à la configuration ou leur scénario au faux moteur, de façon incompatible ; un port `Moteur` modifié deux fois.
- **Rule:**
  - La story S0 transcrit, en une fois et avant toute autre story v2, les formes partagées v2 :
    - contrats §1 v2, §2 v2, §3 v2 (`seed`, `OptionsExport`) ;
    - §11 (rôles, `Artefact` avec `repeat_penalty` et `duree_indicative_s`) ;
    - §13 v2 (scénarios du faux moteur) ;
    - §25 (formes de `domaine/relecture.py`) ;
    - les noms publics de `lot.py` (§9 v2) et la règle d'architecture associée.
  - S0 ne change aucun comportement, **sauf un, nommé [revue A22]** : la permutation des rôles de CAP-7 (`qwen3.5-0.8b-q4km` devient `modele_repli`, `minicpm5-1b-q4km` `candidat`), qui change le modèle choisi quand la RAM disponible est sous `ram_min_defaut_go`. Tous les nouveaux arguments ont un défaut qui reproduit la v0.1.0. La suite complète reste verte, réalignée selon `impacts-v2.md` (lignes 1 à 6 et 13).
  - S0 pose aussi `lot.dossier_lot_existant` (§9, sans effet de bord) et `MOTIF_ID_LOT` borné à 64 caractères **[revue A3/A21]**. `tests/conftest.py` ne change pas : `config_test` relit `config/waveaudit.toml` **[revue A23]**.
  - Les stories v2 suivantes appliquent AD-0 à ces fichiers.
  - **Deux exceptions nommées, sur des valeurs seulement (aucune clé, aucun champ) :**
    - la story de rattachement (CAP-5) peut changer `[recherche] k1` et `b` dans `config/waveaudit.toml` ;
    - la story de rebanc (CAP-6, CAP-7) peut changer `role`, `repeat_penalty` et `duree_indicative_s` des entrées existantes de `config/artefacts.toml`, et `test_config.py::test_manifeste_artefacts` avec eux.
- **Touche :** `domaine/modeles.py`, `domaine/configuration.py`, `domaine/ports.py`, `domaine/relecture.py` (nouveau), `application/lot.py`, `application/incident.py`, `interfaces/cli.py` (import), `installation/manifeste.py`, `config/*.toml`, `tests/faux_moteur.py`, `tests/unitaires/test_architecture.py` ; tests `test_modeles.py`, `test_config.py`, `test_faux_moteur.py`, `test_composition.py`, `e2e/test_lot.py`.

### AD-19 — État de relecture : un fichier, un écrivain, des versions

- **Binds:** V2 CAP-10, CAP-11, CAP-12, CAP-13, CAP-17
- **Prevents:** des corrections perdues entre le fil du lot, la régénération et deux onglets ; un export qui ne lit pas la même vérité que l'UI ; une validation possible en CLI ; une relance qui écrase le travail d'un autre lot.
- **Rule:**
  - L'état de relecture d'un lot est `var/sorties/<id>/relecture.json` (`EtatRelecture`, contrats §25). C'est la seule source des exports final et brouillon (UI et CLI).
  - **Écrivain unique :** `application/relecture.py`. Écriture atomique (`.partiel` puis `os.replace`, retenté sur `PermissionError`), sous un verrou par fichier. Le lot l'alimente entrée par entrée, avant l'événement de fin de fiche.
  - **Règles pures :** dans `domaine/relecture.py` (corriger, valider, remplacer, exporter). Le score CVSS ne vient que de `cvss31`.
  - **Concurrence :** chaque entrée porte une `version`. Toute modification venue de l'UI fournit la version lue : un écart donne `conflit_version` (409), jamais une fusion.
  - **Cycle :** la fiche générée reste immuable jusqu'à un changement de candidat, qui l'efface avec la correction (après confirmation si une correction existe). Toute modification d'une fiche validée la repasse `a_valider`.
  - Aucune commande CLI n'écrit `relecture.json` hors du lot. Relancer crée un nouveau lot.
- **Touche :** `domaine/relecture.py`, `application/relecture.py`, `application/export.py`, `application/lot.py`, `interfaces/web/app.py`, `interfaces/cli.py` ; tests `test_relecture*.py`, `test_export.py`, `e2e/test_relecture_ui.py`, `e2e/test_cli.py`.

### AD-20 — Verrou unique et moteur à la demande

- **Binds:** V2 CAP-9, CAP-11, CAP-14 ; poste 16 Go (une seule instance de llama-server)
- **Prevents:** deux llama-server chargés en même temps (RAM de l'EliteBook) ; une régénération lancée pendant un lot ; un moteur oublié en mémoire après la relecture ; trois verrous différents pour les fiches, l'incident et la régénération.
- **Rule:**
  - Un `VerrouUnique` par processus UI, pris sans attendre par un lot de fiches, un incident ou une régénération. Prise impossible : 409 `lot_en_cours`, avec l'occupation courante (contrats §24).
  - **Moteur à la demande :** `MoteurALaDemande` sert seulement à la régénération. Il passe par `composition.ouvrir`, reste ouvert pour le modèle du lot, et se ferme après `ui.inactivite_moteur_s` (300 s) sans usage, ou à l'arrêt de l'application.
  - Un lot ou un incident, verrou pris, ferme d'abord le moteur à la demande, puis garde son propre cycle de vie (AD-11).
  - La CLI n'utilise ni verrou ni moteur à la demande : un lot CLI concurrent d'un lot UI reste possible, comme en v0.1.0.
  - **[revue A13]** `lot.json` porte le `pid` du processus du lot. Un lot `en_cours` dans un autre processus (pid vivant, journal sans fin) est en lecture seule pour l'UI (409 `lot_en_cours_externe`) et refusé par `waveaudit exporter` (code 2). Le double llama-server reste accepté.
  - **[revue A1/A10]** L'occupation est prise avant la création de l'id (provisoire, puis `definir`) ; verrou et moteur à la demande protègent leur état par un verrou interne et un compteur d'usages.
- **Touche :** `application/moteur_demande.py`, `interfaces/web/app.py`, `config/waveaudit.toml` (`[ui] inactivite_moteur_s`) ; tests `test_moteur_demande.py`, `e2e/test_ui.py`, `e2e/test_relecture_ui.py`, `e2e/test_incident_ui.py`.

### AD-21 — Langue du lot

- **Binds:** V2 CAP-4, CAP-5, CAP-8, CAP-13
- **Prevents:** un lot à moitié anglais (consigne en anglais et repli français, libellés Word dans une langue, garde-fou dans l'autre) ; un catalogue traduit à l'exécution ; un index par langue qui change les rangs de CAP-5.
- **Rule:**
  - **Valeur :** `Langue` (`fr`, `en`), fixée au lancement (`RequeteLot.langue`, sinon `config.fiches.langue`) et consignée dans `lot.json`, `relecture.json` et `lot_demarre`.
  - **Diffusion :** le lot la transmet au workflow par une copie de la configuration (`fiches.langue`), sans changer `REGISTRE` ni le protocole `Workflow`.
  - **Textes :** tous les textes de constat passent par `ConstatType.textes(langue)`. Le catalogue porte ses deux langues (bloc `en`, contrats §15), refusé incomplet au chargement.
  - **Ce qui reste fixe :** l'index BM25 est bilingue et identique pour les deux langues ; le workflow incident et l'UI restent en français.
- **Touche :** `domaine/modeles.py`, `domaine/recherche.py`, `domaine/garde_fous.py`, `workflows/fiches/prompt.py`, `workflows/fiches/pipeline.py`, `adaptateurs/catalogue_yaml.py`, `adaptateurs/export_docx.py`, `application/lot.py`, `application/banc.py`, `interfaces/cli.py`, `interfaces/web/app.py`, `donnees/catalogue/*.yaml` ; tests `test_catalogue.py`, `test_recherche.py`, `test_rattachement_demo.py`, `test_prompt.py`, `test_pipeline.py`, `test_export_docx.py`, `e2e/test_lot.py`, `e2e/test_cli.py`, `e2e/test_ui.py`.

### AD-22 — API HTTP de l'UI : enveloppe de sécurité et état lu sur le disque

- **Binds:** V2 CAP-9 à CAP-15 ; AD-9
- **Prevents:** une page locale pilotée depuis un autre site (CSRF, DNS rebinding) ; un script en ligne ou une ressource externe introduits par une story d'écran ; deux formats d'erreur ; un état de lot perdu au redémarrage du serveur ; des stories web qui se marchent dessus dans `app.py`.
- **Rule:**
  - Les routes, formats JSON, codes d'erreur et limites de taille sont ceux de contrats §26, et seulement ceux-là.
  - **Middleware commun, appliqué à toutes les routes :**
    - Host en liste fermée ;
    - Origin contrôlé sur `POST`/`PUT` ;
    - jeton CSRF par instance (`X-CSRF-Token`) sur `POST`/`PUT` ;
    - `Content-Length` borné ;
    - CSP `default-src 'self'`, `nosniff`, `no-referrer`.
  - Ni script ni style en ligne. Erreurs JSON : `{"detail", "code"}`.
  - **[revue A4/A7]** Aucun GET n'écrit (export en `POST` avec jeton, génération interrompue calculée à la lecture) ; `testserver` n'est accepté que par `creer_app(..., hotes_test=...)` depuis les tests.
  - **État :** l'état d'un lot vient de `journal.jsonl`, `lot.json` et `relecture.json` (`application/lots.py`, `application/relecture.py`), plus l'occupation du verrou. Aucun registre en mémoire.
  - **Structure :** `app.py` assemble des `APIRouter` par surface (pages, lots, relecture, incidents, thème). La première story web pose le middleware, les cinq modules de routeur (vides s'il le faut) **et leur inclusion dans `app.py`**, plus `tests/web_outils.py` ; les suivantes remplissent chacune leur module de routeur sans toucher `app.py` **[revue A28]**.
- **Touche :** `interfaces/web/` (app, routeurs, gabarits, static), `application/lots.py` ; tests `e2e/test_ui.py`, `e2e/test_hors_ligne.py`, `e2e/test_relecture_ui.py`, `e2e/test_incident_ui.py`, `tests/web_outils.py`.

### AD-23 — Qualité de sortie mesurée, pas supposée

- **Binds:** V2 CAP-5, CAP-6, CAP-7
- **Prevents:** des seuils de garde-fou, une consigne ou des rôles de modèles changés sans chiffre ; une recopie mesurée différemment d'un banc à l'autre.
- **Rule:**
  - **Rattachement :** mesuré sans modèle par `test_rattachement_demo.py`, bloquant aux seuils de CAP-5.
  - **Recopie et taux `ok` :** mesurés par `waveaudit banc` (`banc.json` v2, contrats §29), sur le sous-ensemble de 6 notes, sur l'EliteBook, selon `mesures-qualite.md`. **[revue A29-A31]** Une seule définition de la recopie (celle de la référence 0,93 : texte de `fiches.json`, `SequenceMatcher(None, a, b)`, `autojunk` par défaut, replis à part) ; 3 seeds par modèle ; notes « non vues » du rattachement = 21-28 et 30, en `xfail` pendant le réglage.
  - **[revue V1]** Un test `slow` (`e2e/test_reel.py`) rejoue le banc sur 2 notes avec le modèle par défaut et vérifie un plafond de recopie : garde contre un retour vers 0,93, sans remplacer le rebanc.
  - **Changements soumis au rebanc :** consigne (CAP-6), `repeat_penalty` du manifeste et permutation des rôles (CAP-7). Chaque changement est consigné avec ses chiffres dans `bilan-modeles.md`.
  - Une baisse du taux `ok` due aux nouveaux garde-fous est consignée telle quelle.
- **Touche :** `application/banc.py`, `application/composition.py` (`creer_catalogue`), `workflows/fiches/prompt.py`, `config/artefacts.toml`, `tests/unitaires/test_rattachement_demo.py` ; tests `e2e/test_banc.py`.

## Consistency Conventions

| Concern | Convention |
| --- | --- |
| Langue | Identifiants, messages, journaux et documents en français, sans accents dans les identifiants Python. Les termes techniques consacrés restent tels quels (`schema`, `token`). |
| Nommage | Modules `snake_case`, classes `PascalCase`, ports au nom du rôle (`Moteur`, `Catalogue`, `SourceNotes`, `Exporteur`), adaptateurs suffixés par la techno (`MoteurOpenAI`, `CatalogueYaml`). |
| Identifiants de constat | `FAMILLE-SUJET[-PRECISION]` en majuscules ASCII avec tirets, préfixe = famille ; liste minimale figée (contrats §16). |
| Catalogue | Un fichier par famille : `donnees/catalogue/<famille>.yaml` (`web`, `ad`, `infra`, `config`, `crypto`, `autre`), une liste de constats ; schéma `ConstatType` de `formats.md`. |
| Notes de démonstration | `donnees/demo/notes/NN-<id sans préfixe, minuscules>.md` (`01` à `20`), `constat_attendu` pris dans contrats §16. |
| Erreurs | Hiérarchie `ErreurWaveAudit` (contrats §4), aucune n'hérite d'`OSError` ; aucune exception nue ne sort d'un adaptateur. |
| Codes retour CLI | `0` lot terminé (même avec `a_revoir`), `2` entrée ou configuration invalide, `3` moteur injoignable, `4` connexion interdite ou erreur interne, `5` empreinte invalide (contrats §4). |
| Statuts | `ok`, `a_revoir`, `non_traitee`, `non_rattachee` (enum `Statut`). |
| Dates | ISO 8601 avec fuseau (`datetime.now().astimezone()`). |
| Fichiers | `pathlib`, UTF-8 explicite (`utf-8-sig` en lecture des notes), aucun chemin absolu codé en dur ; tout l'état d'exécution sous `var/` (ignoré par git) ; console reconfigurée en UTF-8. |
| Journalisation | `logging` stdlib pour le diagnostic ; `journal.jsonl` pour les événements métier (AD-8). |
| Tests | `tests/unitaires/` et `tests/e2e/`, données de test sous `tests/donnees/`, marqueur `slow` exclu par défaut (`-m "not slow"`), aucun réseau ni vrai modèle hors `slow`. Pour chaque story, les tests ciblés passent puis `ruff check` et `ruff format --check`. |

## Stack

| Name | Version |
| --- | --- |
| Python | 3.12.* (uv) |
| llama.cpp `llama-server` (`llama-b11714-bin-win-cpu-x64.zip`, 19662606 o, sha256 `f78eded047061a3f86372db426797400a2f1bb0ec37868d5927dd820eb3386c0`) | b11714 |
| Défaut : `ibm-granite/granite-4.0-1b-GGUF` `granite-4.0-1b-Q4_K_M.gguf` (1023645440 o, sha256 `22ec0f9cc99a90185312de3c882c84e7bd6789bdd050389844380a01a831d7f1`, Apache-2.0) | commit b27c2fe3f211b7f44e80fa620177aea371099aaa |
| Repli : `openbmb/MiniCPM5-1B-GGUF` `MiniCPM5-1B-Q4_K_M.gguf` (688065920 o, sha256 `81b64d05a23b17b34c475f42b3e72fbde62d4b92cc34541f7a8031d0752deafa`, Apache-2.0) | commit 3d55fac80935ae6456986ad2384b5cbcc4d6c948 |
| Candidat : `unsloth/Qwen3-1.7B-GGUF` `Qwen3-1.7B-Q4_K_M.gguf` (1107409472 o, sha256 `b139949c5bd74937ad8ed8c8cf3d9ffb1e99c866c823204dc42c0d91fa181897`, Apache-2.0) | commit d7f544eead698dbd1f15126ef60b45a1e1933222 |
| Candidat : `unsloth/Qwen3.5-0.8B-GGUF` `Qwen3.5-0.8B-Q4_K_M.gguf` (532517120 o, sha256 `bd258782e35f7f458f8aced1adc053e6e92e89bc735ba3be89d38a06121dc517`, Apache-2.0) | commit 6ab461498e2023f6e3c1baea90a8f0fe38ab64d0 |
| pydantic | 2.14.1 |
| httpx | 0.28.1 |
| fastapi | 0.143.3 |
| uvicorn | 0.54.0 |
| jinja2 | 3.1.6 |
| python-multipart | 0.0.32 |
| typer | 0.27.3 |
| pyyaml | 6.0.3 |
| python-docx | 1.2.0 |
| cvss | 3.6 |
| psutil | 7.2.2 |
| pytest | 9.1.1 |
| pytest-socket | 0.8.1 |
| cyclonedx-bom | 7.5.0 |
| ruff | 0.17.1 |

## Structural Seed

```text
waveaudit/
  pyproject.toml            # package src/, script `waveaudit`, deps épinglées, addopts pytest
  config/
    waveaudit.toml          # défauts (moteur, reseau, recherche, export, ui)
    artefacts.toml          # manifeste : llama-server, modèles, SHA-256, licences
  donnees/
    catalogue/<famille>.yaml
    demo/notes/NN-<sujet>.md
  src/waveaudit/
    domaine/                # modeles.py, ports.py, erreurs.py, configuration.py, recherche.py, garde_fous.py, cvss31.py, incident.py, detection.py, indicateurs.py, garde_fous_incident.py, [v2] relecture.py, qualite_texte.py
    workflows/              # registre.py, fiches/ (pipeline.py, prompt.py)
    adaptateurs/            # moteur_openai.py, llama_server.py, catalogue_yaml.py, notes_fichiers.py, export_docx.py, theme_generique.py, memoire_psutil.py
    application/            # config.py, composition.py, lot.py, journal.py, incident.py, banc.py, [v2] relecture.py, moteur_demande.py, lots.py, export.py
    installation/           # manifeste.py, telechargement.py, sbom.py
    securite/               # garde_reseau.py
    interfaces/             # cli.py, web/ (app.py + [v2] routeurs par surface, templates/, static/ dont tokens.css)
  tests/
    conftest.py  faux_moteur.py
    unitaires/  e2e/  donnees/
  var/                      # ignoré : moteur/, modeles/, sorties/, entrees/, journaux/
  theme-prive/              # ignoré : modele.docx, theme.toml, [v2] web/logo.svg
```

```mermaid
sequenceDiagram
  participant I as CLI ou UI
  participant L as application.lot
  participant W as workflows.fiches
  participant R as domaine.recherche
  participant M as Moteur (llama-server 127.0.0.1)
  participant G as domaine.garde_fous
  participant X as Exporteur docx
  I->>L: executer_lot(requete, config, abonne)
  L->>M: ouvrir (composition) puis sonder()
  loop chaque note (triée)
    L->>W: traiter(note)
    W->>R: top-3 constats
    W->>M: generer_json(prompt, SortieModele)
    W->>G: appliquer(sortie, constat)
    W-->>L: Fiche ou EntreeEcartee
    L->>L: EvenementLot + journal.jsonl
  end
  L->>X: exporter(Rapport) -> rapport.docx
  L-->>I: ResultatLot
```

```mermaid
flowchart LR
  subgraph Poste["Poste consultant (Windows 11, 16 Go, CPU)"]
    nav["Navigateur"] -->|127.0.0.1:8765| web["waveaudit ui"]
    cli["waveaudit fiches"] --> noyau["service de lot"]
    web --> noyau
    noyau -->|127.0.0.1:port libre| llama["llama-server b11714 + GGUF"]
  end
  install["waveaudit installer (seul accès Internet)"] -.->|GitHub, Hugging Face| var[("var/ : binaire, poids vérifiés SHA-256")]
  var --> llama
```

CLI, routes UI, banc et leurs formats : contrats §18 à §20 ; v2 : §23 à §30.

```mermaid
sequenceDiagram
  participant N as Navigateur
  participant W as interfaces/web
  participant V as VerrouUnique
  participant R as application.relecture
  participant D as MoteurALaDemande
  participant F as workflows.fiches
  N->>W: POST /lots/{id}/entrees/{n}/candidat (CSRF, version)
  W->>V: prendre(regeneration)
  W->>R: demarrer_regeneration -> generation=en_cours (relecture.json)
  W-->>N: 202
  W->>R: regenerer (fil)
  R->>D: utiliser(modèle du lot)
  D->>F: rediger(note, constat, candidats)
  F-->>R: Fiche (garde-fous)
  R->>R: remplacer_fiche, version+1 (écriture atomique)
  R->>V: liberer
  N->>W: GET /lots/{id}/entrees/{n} (sondage)
```

## Capability → Architecture Map

| Capability / Area | Lives in | Governed by |
| --- | --- | --- |
| CAP-1 notes | `adaptateurs/notes_fichiers.py`, `domaine/modeles.py` | AD-6, `formats.md` |
| CAP-2 catalogue | `donnees/catalogue/`, `adaptateurs/catalogue_yaml.py`, `waveaudit catalogue verifier` | AD-16, contrats §15-16 |
| CAP-3 recherche | `domaine/recherche.py` | AD-7 |
| CAP-4 adaptation | `workflows/fiches/`, `adaptateurs/moteur_openai.py` | AD-3, AD-4, AD-6 |
| CAP-5 garde-fous | `domaine/garde_fous.py` | AD-5 |
| CAP-6 Word | `adaptateurs/export_docx.py` | AD-8, AD-14 |
| CAP-7 CLI | `interfaces/cli.py`, `application/lot.py` | AD-2, AD-6, AD-8, codes retour |
| CAP-8 UI | `interfaces/web/` | AD-2, AD-9 |
| CAP-9 moteur interchangeable | `application/config.py`, `adaptateurs/moteur_openai.py` | AD-3, AD-11, AD-13 |
| CAP-10 installation | `installation/`, `config/artefacts.toml` | AD-12 |
| CAP-11 hors ligne + SBOM | `securite/garde_reseau.py`, `tests/e2e/test_hors_ligne.py`, `installation/sbom.py` | AD-9, AD-12 |
| CAP-12 banc | `application/banc.py`, `adaptateurs/memoire_psutil.py` | AD-8, AD-11, contrats §20 |
| Socle partagé | `domaine/`, `config/`, `tests/conftest.py`, `tests/faux_moteur.py` | AD-0, AD-16, AD-18 |
| V2 CAP-1 seed + 1 | `workflows/*/pipeline.py`, `adaptateurs/moteur_openai.py`, `domaine/ports.py` | AD-6, AD-18, contrats §5 |
| V2 CAP-2 échappement | `workflows/*/prompt.py` | AD-4, contrats §8 |
| V2 CAP-3, CAP-4 garde-fous | `domaine/garde_fous*.py`, `domaine/qualite_texte.py` | AD-5, contrats §6, §21 |
| V2 CAP-5 rattachement | `domaine/recherche.py`, `donnees/catalogue/` | AD-7, AD-23 |
| V2 CAP-6, CAP-7 recopie et rôles | `workflows/fiches/prompt.py`, `config/artefacts.toml`, `application/banc.py` | AD-12, AD-23, contrats §11, §29 |
| V2 CAP-8 anglais | catalogue bilingue, prompt, export, CLI, UI | AD-21, contrats §15, §23, §27 |
| V2 CAP-9, CAP-10 création, suivi, lots récents | `interfaces/web/`, `application/lots.py` | AD-20, AD-22, contrats §26, §30 |
| V2 CAP-11, CAP-12 relecture, correction, validation | `domaine/relecture.py`, `application/relecture.py`, `application/moteur_demande.py`, `interfaces/web/` | AD-19, AD-20, contrats §24 à §26 |
| V2 CAP-13, CAP-17 exports | `application/export.py`, `adaptateurs/export_docx.py`, `interfaces/cli.py` | AD-8, AD-19, contrats §27 |
| V2 CAP-14 incident dans l'UI | `interfaces/web/`, `application/incident.py` | AD-17, AD-20, AD-22 |
| V2 CAP-15 thème et accessibilité | `interfaces/web/static/`, `templates/` | AD-14, AD-22, contrats §28 |
| V2 CAP-16 contrat aligné | `contrats.md`, `application/lot.py` | AD-18, contrats §9 |

## Deferred

- Choix final du modèle et réglage du prompt : sur l'EliteBook, hors nuit, avec la méthode de `slm-quality-bench`. Le manifeste et la configuration suffisent à en changer.
- Valeurs fines de `-c`, `-t` et du seuil RAM : réglées au banc réel (CAP-12). Défauts de départ : `ctx` 4096, 4 threads, `ram_min_defaut_go` 4,5.
- Workflow CERT : spécifié dans SPEC-waveaudit-cert et AD-17, développé après le MVP.
- Installateur Windows packagé (Inno Setup), variante archive hors ligne des poids : après les retours des testeurs.
- Authentification vers un LLM interne Wavestone : à définir quand l'endpoint existera ; `Configuration.moteur.cle_api` est seulement prévue.
- Contenu de la charte Word Wavestone (`modele.docx`) et logo : hors dépôt (AD-14). La palette web est publique depuis la v2.
- (Levé, story D2) CI GitHub Actions : `.github/workflows/ci.yml` (windows-latest, `uv sync --locked`, `ruff check`, `ruff format --check`, suite hors `slow`) existe et doit rester verte ; la suite locale reste la référence avant intégration. **[revue A25]**
- (Levé en V1) Mode JSON : `json_schema` fonctionne sur les 4 modèles ; `reflexion = false` est requis pour MiniCPM5 et Qwen3.5 (contrats §22).
- Pas d'authentification sur l'UI locale au-delà des contrôles Host/Origin et du jeton CSRF par instance (contrats §26) : suffisant pour des données fictives sur un poste mono-utilisateur, à revoir au pilote.
- Passage du moteur du lot au moteur à la demande, sans rechargement : la première régénération après un lot paie le chargement du modèle. À revoir si la mesure sur l'EliteBook le rend gênant.
- Verrou entre processus (lot CLI concurrent d'un lot UI) : hors v2, accepté par Anaël (2026-10-18) ; deux llama-server restent possibles dans ce cas, comme en v0.1.0, limite documentée dans le README v2. Verrou fichier en v3 si besoin.
- Persistance de l'état du tiroir (ouvert ou replié) : confort local, non contractuel (EXPERIENCE).
- Langue du rapport d'incident : français seulement en v2.
