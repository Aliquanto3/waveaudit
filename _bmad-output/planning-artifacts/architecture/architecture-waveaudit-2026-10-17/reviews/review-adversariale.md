# Revue adversariale du spine WaveAudit POC (2026-10-17)

Objet : `ARCHITECTURE-SPINE.md`, avec `formats.md` et `SPEC.md`.
Méthode : pour chaque trou, deux unités (stories ou modules) qui respectent chaque AD à la lettre et qui pourtant ne s'assemblent pas. On donne le trou, un scénario concret de divergence, et une correction prête à coller (nouvel AD ou Rule resserrée).

## Verdict

Le spine fixe bien les choix techniques (moteur, BM25, garde-fous, hors ligne, manifeste), mais il ne fixe pas les **formes partagées** ni les **propriétaires** : `Fiche`, `RequeteLot`, `ResultatLot`, `Configuration`, le protocole `Workflow` et les ports `Catalogue`, `SourceNotes`, `Exporteur` sont nommés sans être définis. Il contient en outre trois contradictions internes (AD-1 contre AD-12, AD-1 contre le banc, AD-1 contre AD-15). Lancés tels quels cette nuit, des agents indépendants produiront des modules qui passent chacun leurs tests et ne s'intègrent pas. Il faut une story « socle » séquentielle, avant toute autre, qui écrit les types, les ports, la configuration et les fichiers partagés, plus les AD ci-dessous.

---

## Critique

### C1. Aucun propriétaire des fichiers partagés : `pyproject.toml`, `uv.lock`, `tests/conftest.py`, `config/waveaudit.toml`, `domaine/modeles.py`, `domaine/ports.py`, `domaine/erreurs.py`

- **Unités en conflit :** toutes les stories, par paires. Par exemple la story moteur (AD-3) et la story garde réseau (AD-9).
- **Trou :** chaque story a besoin d'ajouter ses dépendances, ses `addopts`, sa section de configuration, ses modèles et sa fixture. Le spine ne dit pas qui crée ces fichiers.
- **Scénario :** la story moteur ajoute `httpx` et la fixture `faux_moteur` à `conftest.py`. La story garde réseau ajoute `pytest-socket` et réécrit `addopts`. La story CLI crée son propre `domaine/modeles.py` avec une `Fiche` minimale. À l'intégration, on a trois versions de `conftest.py`, deux de `modeles.py` et un `uv.lock` régénéré trois fois. Les conflits ne se résolvent pas mécaniquement, parce que les classes ont des champs différents.
- **Correction (nouvel AD) :**

> ### AD-0 — Socle commun, livré avant toute autre story
> - **Binds:** all
> - **Rule:**
>   - Une story `socle` est exécutée et intégrée **seule et en premier**. Elle crée : `pyproject.toml` (toutes les dépendances de la table Stack, épinglées, `addopts = "-m 'not slow' --allow-hosts=127.0.0.1,::1"`, config ruff), `uv.lock`, l'arborescence de la Structural Seed avec des `__init__.py`, `domaine/modeles.py`, `domaine/ports.py`, `domaine/erreurs.py`, `domaine/configuration.py`, `config/waveaudit.toml`, `config/artefacts.toml`, `workflows/registre.py` (protocole seulement), `tests/conftest.py` (fixtures `faux_moteur` et `config_test`), `tests/faux_moteur.py` et `tests/unitaires/test_architecture.py`.
>   - Les stories suivantes **ne modifient pas** ces fichiers. Si l'une d'elles a besoin d'un champ, d'une dépendance ou d'une fixture qui manque, elle s'arrête et le signale : elle ne l'ajoute pas.
>   - Exception : une story peut ajouter un fichier de test à elle (`tests/unitaires/test_<module>.py`) et des fixtures locales dans ce fichier.

### C2. `Fiche`, `Motif`, `Tracabilite` et le sort des entrées écartées ne sont pas définis, et AD-8 contredit AD-14

- **Unités en conflit :** `domaine/garde_fous.py` (qui produit la fiche) et `adaptateurs/export_docx.py` (qui la consomme). Aussi `application/lot.py` (`fiches.json`) et `application/banc.py` (le taux de constats retrouvés).
- **Trou :** `formats.md` donne des rubriques en prose, pas des noms de champs. AD-8 dit « l'exporteur ne lit que des `Fiche` », alors qu'AD-14 exige une annexe des `non_traitee` et `non_rattachee`, qui n'ont « pas de fiche » (AD-6). L'enum `Statut` a quatre valeurs, mais `formats.md` limite le statut d'une fiche à `ok` ou `a_revoir`. AD-7 garde les 3 premiers candidats « dans la traçabilité de la fiche » sans en donner la forme. Le banc a besoin de `constat_attendu`, que rien ne transporte.
- **Scénario :** la story garde-fous écrit `Fiche(vecteur_cvss="CVSS:3.1/…", score=7.5, motifs=["CWE-9999 retiré"])`. La story export lit `fiche.cvss.vecteur` et `fiche.tracabilite.note`. Pour l'annexe, l'exporteur crée des « `Fiche` vides » avec `statut=non_traitee`, ce qui casse la validation pydantic des rubriques. Le banc relit les notes sur le disque pour retrouver `constat_attendu`, en violation de l'esprit d'AD-8.
- **Correction (nouvel AD, `domaine/modeles.py`) :**

> ### AD-16 — Modèles partagés (forme exacte)
> - **Binds:** CAP-1 à CAP-8, CAP-12
> - **Rule:** `domaine/modeles.py` définit exactement ces modèles pydantic, tous en `model_config = ConfigDict(extra="forbid", frozen=True)` :
>   ```python
>   class Statut(StrEnum): OK="ok"; A_REVOIR="a_revoir"; NON_TRAITEE="non_traitee"; NON_RATTACHEE="non_rattachee"
>   class Reference(BaseModel): id: str; titre: str; url: str
>   class ConstatType(BaseModel):
>       id: str; titre: str; famille: Literal["web","ad","infra","config","crypto","autre"]
>       mots_cles: list[str]; description: str; impact: str; recommandation: str
>       cvss_vecteur: str; references: list[Reference]  # au moins 1
>       source: str
>   class Note(BaseModel):
>       fichier: str            # nom de fichier seul, jamais un chemin ("01-xss-reflechi.md")
>       titre: str | None; actif: str | None
>       severite_pressentie: Literal["critique","elevee","moyenne","faible","info"] | None
>       constat_attendu: str | None   # transporté, jamais lu par la recherche ni le prompt
>       corps: str              # non vide après strip
>   class NoteInvalide(BaseModel): fichier: str; raison: str
>   class MetriquesCvss(BaseModel): AV: Literal["N","A","L","P"]; AC: Literal["L","H"]; PR: Literal["N","L","H"]; UI: Literal["N","R"]; S: Literal["U","C"]; C: Literal["N","L","H"]; I: Literal["N","L","H"]; A: Literal["N","L","H"]
>   class Cvss(BaseModel): vecteur: str; score: float; severite: Literal["aucune","faible","moyenne","elevee","critique"]
>   class CodeMotif(StrEnum): REFERENCE_RETIREE="reference_retiree"; VECTEUR_INVALIDE="vecteur_invalide"; RUBRIQUE_COMPLETEE="rubrique_completee"; REPLI_SORTIE_INVALIDE="repli_sortie_invalide"; REPLI_MOTEUR="repli_moteur"; NOTE_INVALIDE="note_invalide"; AUCUN_CONSTAT="aucun_constat"
>   class Motif(BaseModel): code: CodeMotif; detail: str
>   class Candidat(BaseModel): id: str; score: float
>   class Tracabilite(BaseModel): note: str; constat_id: str; candidats: list[Candidat]; constat_attendu: str | None
>   class Fiche(BaseModel):
>       titre: str; description: str; impact: str; recommandation: str
>       cvss: Cvss; references: list[Reference]
>       statut: Literal[Statut.OK, Statut.A_REVOIR]; motifs: list[Motif]
>       tracabilite: Tracabilite
>   class EntreeEcartee(BaseModel):
>       note: str; statut: Literal[Statut.NON_TRAITEE, Statut.NON_RATTACHEE]
>       motif: Motif; candidats: list[Candidat]; constat_attendu: str | None
>   ResultatElement = Fiche | EntreeEcartee
>   ```
> - AD-8 devient : « `fiches.json` = `{"fiches": [Fiche…], "ecartees": [EntreeEcartee…]}` sérialisé par `model_dump(mode="json")`. L'exporteur ne lit que des `Fiche` et des `EntreeEcartee`. »
> - Invariant : `statut == a_revoir` si et seulement si `motifs` n'est pas vide.

### C3. Le protocole `Workflow` (AD-15) est incompatible avec AD-1, AD-2 et le diagramme de séquence

- **Unités en conflit :** `workflows/fiches/pipeline.py` et `application/lot.py`. Aussi `workflows/registre.py` et `application/composition.py`.
- **Trous :**
  1. `preparer(config)` reçoit une `Configuration`, qui vit dans `application/config.py`. Or AD-1 interdit à `workflows/` d'importer `application`. Le test d'architecture échouera, ou l'agent typera `config: Any`.
  2. Les ports ne sont injectés nulle part. `registre.py` (dans `workflows/`) ne peut pas importer la composition. Seule la composition instancie des adaptateurs. Comment `traiter` obtient-il le `Moteur` et le `Catalogue` ?
  3. `assembler(resultats) -> Rapport` : le type `Rapport` n'existe pas. Le diagramme montre `L->>X: exporter(fiches)`, c'est-à-dire que le lot exporte.
  4. Le diagramme dit `W-->>L: Fiche + EvenementLot`, alors qu'AD-15 dit `traiter -> ResultatElement`. Qui émet `fiche_demarree` et mesure `duree_s` ?
  5. Qui énumère les éléments ? Les notes sont propres à `fiches`. Le lot générique ne devrait pas connaître `SourceNotes`.
- **Scénario :** l'agent du pipeline écrit `class WorkflowFiches: def preparer(self, config): self.catalogue = CatalogueYaml(config.catalogue.dossier)`, ce qui viole AD-1. L'agent du lot écrit `wf.traiter(note)` et attend un tuple `(Fiche, EvenementLot)`. L'agent de la composition expose `construire(config) -> dict[str, object]`. Rien ne s'emboîte.
- **Correction (AD-15 resserré, et déplacement de la configuration) :**

> - `Configuration` (le modèle pydantic) vit dans `domaine/configuration.py`. Le **chargement** (lecture TOML, fusion, validation) vit dans `application/config.py` : `charger_configuration(chemin: Path | None) -> Configuration`.
> - `domaine/ports.py` définit `@dataclass(frozen=True) class Ports: moteur: Moteur; catalogue: Catalogue; source_notes: SourceNotes; exporteur: Exporteur; prefixe_systeme: str`.
> - `workflows/registre.py` : `REGISTRE: dict[str, Callable[[Configuration, Ports], Workflow]]`, qui associe un nom à une **fabrique**, avec `{"fiches": workflows.fiches.pipeline.creer}`.
> - Protocole :
>   ```python
>   class Workflow(Protocol):
>       def preparer(self, dossier: Path) -> list[Note | NoteInvalide]   # lit via ports.source_notes, trié
>       def traiter(self, element: Note | NoteInvalide) -> ResultatElement  # n'émet aucun événement
>       def assembler(self, resultats: list[ResultatElement]) -> Rapport
>   class Rapport(BaseModel): fiches: list[Fiche]; ecartees: list[EntreeEcartee]
>   ```
> - `application/lot.py` est le **seul** émetteur d'`EvenementLot`. Il chronomètre `traiter`, écrit `fiches.json` et appelle `ports.exporteur.exporter(rapport, chemin)`. Le workflow n'écrit aucun fichier.

### C4. Le schéma de `Configuration` n'est pas figé

- **Unités en conflit :** `application/config.py` et chaque consommateur : `moteur_openai`, `llama_server`, `garde_reseau`, `web/app.py`, `banc`, `garde_fous` (longueurs maximales).
- **Trou :** AD-3, AD-9, AD-11 et AD-13 citent des champs épars (`moteur.mode`, `moteur.ram_min_defaut_go`, `moteur.delai_demarrage_s`, `reseau.hotes_autorises`, `ui.hote`), mais pas leurs noms exacts (`timeout` ou `timeout_s` ?), ni leurs types, ni leurs défauts. `moteur.modele` mélange le nom d'une entrée du manifeste (en `local-gere`) avec la valeur du champ `model` de l'API (en `externe`). « Longueur maximale bornée par la configuration » ne dit pas quelle clé.
- **Scénario :** la story config déclare `extra="forbid"` et `moteur.timeout_s`. La story moteur lit `config.moteur.timeout` et ajoute `timeout = 120` dans `waveaudit.toml`. Au chargement : `ConfigurationInvalide`. Variante : `extra="allow"`, et la faute de frappe passe en silence avec un défaut différent dans chaque module.
- **Correction (AD-13 resserré, avec le contenu exact de `config/waveaudit.toml`) :**

> - Toutes les sections sont en `extra="forbid"`. Les clés, types et défauts sont exactement :
>   ```toml
>   [moteur]
>   mode = "local-gere"          # "local-gere" | "externe"
>   base_url = ""                # externe : URL complète se terminant par /v1, ex. "http://127.0.0.1:8080/v1"
>   modele = ""                  # nom d'une entrée du manifeste ; vide = choix auto défaut/repli (AD-11)
>   modele_api = ""              # valeur du champ "model" envoyé ; vide = nom de l'entrée du manifeste
>   prefixe_systeme = ""         # utilisé seulement en externe ; en local-gere il vient du manifeste
>   cle_api = ""                 # vide = pas d'en-tête Authorization
>   timeout_s = 180.0
>   temperature = 0.2
>   seed = 42
>   max_tokens = 700
>   longueur_max_rubrique = 1200 # caractères, appliquée à titre/description/impact/recommandation
>   taille_max_note = 6000       # caractères du corps envoyés au modèle (troncature au-delà)
>   ctx = 4096
>   threads = 4
>   ram_min_defaut_go = 4.5
>   delai_demarrage_s = 120.0
>   [reseau]
>   hotes_autorises = ["127.0.0.1", "::1", "localhost"]
>   [recherche]
>   k1 = 1.5
>   b = 0.75
>   [chemins]                    # relatifs à racine_projet()
>   var = "var"
>   catalogue = "donnees/catalogue"
>   theme_prive = "theme-prive"
>   manifeste = "config/artefacts.toml"
>   [ui]
>   hote = "127.0.0.1"
>   port = 8765
>   ```
> - `application/config.py` expose `racine_projet() -> Path` (le dossier qui contient `config/waveaudit.toml`, résolu depuis le paquet). Tout chemin relatif de la configuration est résolu contre lui, jamais contre `Path.cwd()`.
> - `waveaudit.local.toml` est cherché dans `racine_projet()`.

### C5. Les identifiants de constat attendus dans les notes de démonstration ne sont liés à rien

- **Unités en conflit :** la story catalogue (`donnees/catalogue/*.yaml`, au moins 30 entrées) et la story notes de démonstration (`donnees/demo/notes/NN-*.md`, `constat_attendu`). Le banc (CAP-3, 18/20 et 15/20) dépend des deux.
- **Trou :** la convention fixe la forme `FAMILLE-SUJET[-PRECISION]`, pas la liste. Deux agents qui ne se parlent pas inventeront des identifiants différents.
- **Scénario :** le catalogue contient `WEB-INJECTION-SQL`. La note `03-sqli.md` attend `WEB-SQLI`. CAP-3 tombe à 0/20 alors que la recherche est correcte, et aucun test unitaire ne le voit.
- **Correction (convention resserrée, liste figée dans le spine) :**

> - **Identifiants figés.** Le catalogue contient au moins ces 35 identifiants (d'autres peuvent s'ajouter) :
>   web : `WEB-XSS-REFLECHI`, `WEB-XSS-STOCKE`, `WEB-INJECTION-SQL`, `WEB-CSRF`, `WEB-IDOR`, `WEB-SSRF`, `WEB-TRAVERSEE-CHEMIN`, `WEB-UPLOAD-NON-RESTREINT`, `WEB-SESSION-FIXATION`, `WEB-ENTETES-SECURITE`, `WEB-CORS-PERMISSIF`, `WEB-REDIRECTION-OUVERTE`, `WEB-DIVULGATION-ERREURS`, `WEB-AUTH-FORCE-BRUTE`, `WEB-XXE`, `WEB-DESERIALISATION` ;
>   ad : `AD-KERBEROASTING`, `AD-ASREP-ROASTING`, `AD-DELEGATION-NON-CONTRAINTE`, `AD-LAPS-ABSENT`, `AD-ADMINS-EXCESSIFS`, `AD-GPP-MOT-DE-PASSE` ;
>   infra : `INFRA-SMB-SIGNATURE`, `INFRA-SERVICE-OBSOLETE`, `INFRA-SNMP-COMMUNAUTE`, `INFRA-RDP-EXPOSE`, `INFRA-LLMNR-NBTNS` ;
>   config : `CONFIG-MOT-DE-PASSE-DEFAUT`, `CONFIG-SECRETS-EN-CLAIR`, `CONFIG-LISTAGE-REPERTOIRE`, `CONFIG-DEBUG-ACTIF` ;
>   crypto : `CRYPTO-TLS-OBSOLETE`, `CRYPTO-CERTIFICAT-INVALIDE`, `CRYPTO-HACHAGE-FAIBLE` ;
>   autre : `AUTRE-JOURNALISATION-INSUFFISANTE`.
> - Le préfixe de l'identifiant correspond à la famille et au nom du fichier (`WEB-` dans `web.yaml`) ; `catalogue verifier` le contrôle.
> - **Notes 01 à 20** : chaque `constat_attendu` est pris dans cette liste, avec 20 identifiants distincts, dont au moins 3 en `ad`, 2 en `infra`, 2 en `crypto` et 2 en `config`. Le nom de fichier est `NN-<id en minuscules sans préfixe>.md`, par exemple `01-xss-reflechi.md`.

### C6. AD-1 contredit d'autres AD, et le test d'architecture fera échouer des stories conformes

- **Unités en conflit :** `tests/unitaires/test_architecture.py` (AD-1) contre `installation/telechargement.py` (AD-12), `application/banc.py` (spine) et `interfaces/cli.py`, commande `ui`.
- **Trous :**
  - AD-12 télécharge depuis `installation/`, mais « seul `adaptateurs/` importe `httpx` ».
  - Le banc « via psutil » vit dans `application/`, mais « seul `adaptateurs/` importe `psutil` ».
  - La commande `ui` doit lancer `uvicorn.run`, et `uvicorn` n'est attribué à aucun module. `jinja2` non plus.
  - Le périmètre du test n'est pas dit : `tests/faux_moteur.py` importe `fastapi` hors de `interfaces/web/`.
  - `installation/` est hors de toute règle d'import. Qui peut l'importer ? `adaptateurs/llama_server.py` en a besoin pour les chemins.
- **Scénario :** la story installation importe `httpx` dans `telechargement.py`, comme le dit AD-12. La story socle a écrit le test d'architecture à la lettre d'AD-1 : la suite échoue à l'intégration, et le reviewer doit choisir entre deux AD.
- **Correction (AD-1 resserré, en remplaçant la deuxième puce) :**

> - Imports réservés (analyse limitée à `src/waveaudit/`) :
>   - `httpx` : `adaptateurs/` et `installation/telechargement.py` ;
>   - `psutil` : `adaptateurs/` seulement. Le banc mesure la mémoire par le port `MesureMemoire.rss_octets(pid: int) -> int | None` (adaptateur `adaptateurs/memoire_psutil.py`) ;
>   - `yaml`, `docx` : `adaptateurs/` ;
>   - `fastapi`, `jinja2`, `python_multipart` : `interfaces/web/` ;
>   - `uvicorn`, `typer` : `interfaces/cli.py` ;
>   - `installation` : importé seulement par `application/` et `interfaces/cli.py`. La composition résout les chemins du manifeste et les passe aux adaptateurs en arguments.
> - `tests/` n'est pas soumis à ces règles.

### C7. `RequeteLot`, `ResultatLot` et l'identifiant de lot ne sont pas définis

- **Unités en conflit :** `interfaces/web/app.py` (`var/entrees/<id>/`, `/lots/{id}/…`) et `application/lot.py` (`var/sorties/<AAAAMMJJ-HHMMSS>/`). Aussi `interfaces/cli.py` (`-o rapport.docx`, `--modele`) et `application/banc.py`.
- **Trous :** deux identifiants sans lien entre eux. Deux lots lancés dans la même seconde se télescopent (tests, ou CLI pendant l'UI). On ne sait pas si `-o` remplace le rapport de `var/sorties` ou s'y ajoute. Le nom du workflow (AD-15) et `--modele` n'ont pas de place définie.
- **Scénario :** l'UI génère un `uuid4` pour `var/entrees/<uuid>/`. Le lot écrit dans `var/sorties/20261017-231502/`. `GET /lots/<uuid>/rapport.docx` ne retrouve pas le fichier. Dans les tests e2e, deux lots dans la même seconde écrasent mutuellement leur `journal.jsonl`.
- **Correction (AD-2 resserré) :**

> ```python
> class RequeteLot(BaseModel):
>     dossier: Path                    # dossier d'entrée (notes)
>     workflow: str = "fiches"
>     modele: str | None = None        # surcharge moteur.modele (local-gere) ou moteur.modele_api (externe)
>     id_lot: str | None = None        # None = généré par le lot
>     copie_rapport: Path | None = None  # -o : copie de rapport.docx, en plus de var/sorties/<id>/
> class ResultatLot(BaseModel):
>     id_lot: str; dossier_sortie: Path; rapport: Rapport; chemin_rapport: Path; duree_s: float
> ```
> - `application.lot.nouvel_id_lot(var: Path) -> str` renvoie `AAAAMMJJ-HHMMSS`, avec un suffixe `-2`, `-3`… si `var/sorties/<id>` existe déjà. La création du dossier est atomique (`mkdir(exist_ok=False)` et nouvel essai).
> - L'UI appelle `nouvel_id_lot`, écrit dans `var/entrees/<id_lot>/` et passe `id_lot` dans la requête. `id_lot` est le même partout (`entrees`, `sorties`, routes).
> - `executer_lot` lève `EntreeInvalide` (dossier absent, aucune note) et `MoteurInjoignable` (sonde initiale). Elle ne lève rien d'autre pour une fiche.

### C8. Qui valide la sortie du modèle ? Le scénario `vecteur_invalide` est injoignable, et `erreur_500` n'est pas classé

- **Unités en conflit :** `adaptateurs/moteur_openai.py` (AD-3 : « lève `SortieInvalide` si hors schéma »), `workflows/fiches/pipeline.py` et `domaine/garde_fous.py` (AD-5, étape 3 : « si le vecteur est invalide »).
- **Trous :**
  - Valider un JSON contre un `schema: dict` demande `jsonschema`, absent de la Stack.
  - Si la validation se fait contre `SortieModele` avec des enums, un vecteur invalide devient une `SortieInvalide`, puis un nouvel essai, puis un repli. L'étape 3 d'AD-5 n'est alors jamais atteinte. Toute combinaison de métriques valides donne d'ailleurs un vecteur 3.1 valide.
  - Une réponse HTTP 500 n'est ni « connexion refusée ou timeout » ni « non JSON ».
  - `SortieModele` est statique dans le domaine alors que sa longueur maximale vient de la configuration.
- **Scénario :** l'agent du moteur valide avec pydantic et lève `SortieInvalide` sur `"AV": "X"`. Le test CAP-5 de la story garde-fous (faux moteur `vecteur_invalide`) attend un seul appel, `motifs[0].code == "vecteur_invalide"` et le vecteur par défaut. Il observe deux appels et `repli_sortie_invalide`. Pour `erreur_500`, un agent attend un nouvel essai (deux requêtes), l'autre un repli immédiat (une requête).
- **Correction (AD-3 et AD-4 resserrés) :**

> - `Moteur.generer_json` lève `SortieInvalide` **seulement** si `choices[0].message.content` n'est pas du JSON, ou si ce n'est pas un objet. Il ne valide pas le schéma. Il lève `MoteurInjoignable` pour une connexion refusée, un timeout (`moteur.timeout_s`) ou un statut HTTP autre que 200 (un 500 donne donc un repli sans nouvel essai).
> - `domaine/modeles.py` expose `schema_sortie(longueur_max: int) -> dict`. C'est le JSON Schema envoyé au moteur : sans `$ref` ni `$defs`, avec `additionalProperties: false` à chaque niveau, des enums CVSS et `maxLength`.
> - Le workflow valide les quatre rubriques (chaînes présentes) et lève `SortieInvalide` sinon, ce qui donne un nouvel essai. Les métriques `cvss` sont passées **brutes** (`dict`) à `garde_fous.appliquer(sortie_brute, constat, note, candidats) -> Fiche`. Une métrique absente ou hors enum y donne le vecteur par défaut, avec le motif `vecteur_invalide`, sans nouvel essai.
> - Le scénario `vecteur_invalide` du faux moteur renvoie `"AV": "X"` avec des rubriques valides.

---

## Élevé

### E1. `base_url` avec ou sans `/v1`, et une sonde absente du port

- **Unités :** `adaptateurs/moteur_openai.py` (`POST {base_url}/chat/completions`), `tests/faux_moteur.py` (`/health`, `/v1/models`, `/v1/chat/completions`), `application/lot.py` (« sonde `/health` ou `/models` ») et `adaptateurs/llama_server.py` (`/health`).
- **Trou :** pour que `{base_url}/chat/completions` tombe sur `/v1/chat/completions`, `base_url` doit finir par `/v1`. Mais alors `{base_url}/health` vaut `/v1/health`, qui n'existe pas. Le port `Moteur` n'a d'ailleurs pas de méthode de sonde, donc le lot ne peut sonder que par HTTP, ce qui viole AD-1.
- **Scénario :** la fixture renvoie `http://127.0.0.1:p` sans `/v1`, et tous les appels de génération reçoivent un 404. Ou bien le lot sonde `{base_url}/health`, reçoit un 404, conclut que le moteur est injoignable et sort avec le code 3 sur un faux moteur nominal.
- **Correction :**

> - `base_url` se termine toujours par `/v1` (fixture, configuration, gestionnaire llama-server).
> - Le port `Moteur` ajoute `sonder() -> None` : `GET {base_url}/models`, qui lève `MoteurInjoignable` si le statut n'est pas 200. Le lot appelle `ports.moteur.sonder()` une fois, avant `lot_demarre`.
> - Seul `llama_server.py` interroge `GET <racine>/health`, la racine étant `base_url` sans `/v1`, pendant le démarrage.
> - Le client `httpx` est créé avec `trust_env=False` (voir E3).

### E2. `EvenementLot` : types manquants, champs non typés, et deux écrivains possibles du journal

- **Unités :** `application/lot.py`, l'abonné de `interfaces/cli.py`, l'abonné de `interfaces/web/app.py` et `application/banc.py`.
- **Trous :**
  - Il n'y a pas de type pour `non_rattachee` : faut-il `fiche_terminee` avec ce statut, ou `fiche_non_traitee` ?
  - Il n'y a pas d'événement d'échec du lot (sonde KO), ce qui laisse l'UI bloquée « en cours ».
  - Le type d'`horodatage`, la base d'`index` (0 ou 1), la valeur de `note` pour les événements de lot et la forme de `details` ne sont pas dits.
  - « Chaque événement est écrit dans `journal.jsonl` » ne dit pas par qui. Si c'est l'abonné, la CLI et l'UI écrivent chacune leur version, ou les deux écrivent.
  - Une exception levée par l'abonné tue-t-elle le lot ?
- **Scénario :** le lot émet `fiche_non_traitee` pour une note non rattachée. Le test UI compte les `fiche_terminee` et attend 20, il en voit 19. L'abonné CLI écrit aussi `journal.jsonl`, d'où des lignes en double. Le banc lit `index` comme 0-based et décale ses durées.
- **Correction (AD-8 resserré) :**

> ```python
> class TypeEvenement(StrEnum): LOT_DEMARRE="lot_demarre"; FICHE_DEMARREE="fiche_demarree"; FICHE_TERMINEE="fiche_terminee"; FICHE_NON_TRAITEE="fiche_non_traitee"; FICHE_NON_RATTACHEE="fiche_non_rattachee"; LOT_TERMINE="lot_termine"; LOT_ECHOUE="lot_echoue"
> class EvenementLot(BaseModel):
>     type: TypeEvenement; horodatage: datetime  # aware, sérialisé ISO 8601
>     index: int | None   # 1..total pour les événements de fiche, None sinon
>     total: int; note: str | None   # nom de fichier
>     statut: Statut | None; duree_s: float | None
>     details: dict[str, str | int | float | None] = {}
> ```
> - `lot_demarre.details = {"id_lot", "modele", "pid_moteur"}`, où `pid_moteur` vaut `None` en externe. `lot_echoue.details = {"erreur": <classe>, "message"}`, émis puis exception relevée.
> - **Seul `application/lot.py` écrit `journal.jsonl`** (`model_dump_json()`, une ligne, flush), **avant** d'appeler l'abonné. Une exception de l'abonné est journalisée par `logging` et ignorée.
> - Une sonde KO donne `lot_echoue` sans `lot_demarre`. Le dossier de sortie est créé avant la sonde, pour que le journal existe.

### E3. Garde réseau : ordre d'initialisation, fuite entre tests, proxy, et API d'enregistrement non définie

- **Unités :** `securite/garde_reseau.py`, `interfaces/cli.py`, `tests/e2e/test_hors_ligne.py`, `tests/conftest.py` (pytest-socket et faux moteur) et `adaptateurs/moteur_openai.py`.
- **Trous :**
  1. « Première instruction » est impossible, parce que `hotes_autorises` vient de la `Configuration`, qu'il faut charger avant.
  2. Le patch est global au processus. Avec `CliRunner` (en processus), le garde activé par le test CLI reste actif pour tous les tests suivants, puisqu'aucun `desactiver` n'est prévu.
  3. `test_hors_ligne` doit « enregistrer toute tentative », mais `activer` ne fait que lever une exception. Où l'enregistrement se lit-il ?
  4. `connect` reçoit une adresse IP, pas un nom : `localhost`, ou le nom d'hôte d'un futur LLM interne dans la liste, ne correspondra jamais.
  5. `httpx` lit par défaut `HTTP(S)_PROXY`. Sur un poste d'entreprise avec proxy, l'appel à `127.0.0.1` part vers le proxy : `ConnexionInterdite` en prod et `MoteurInjoignable` dans les tests. Cela contourne aussi AD-13, qui interdit `os.environ`.
  6. `ConnexionInterdite` levée dans `connect` sous httpcore : si elle hérite d'`OSError`, httpx la convertit en `ConnectError`, puis en `MoteurInjoignable`, et la violation est masquée en repli.
  7. Le lot UI testé par `TestClient` ne passe jamais par la commande `ui`, donc le garde n'y est jamais activé.
  8. L'ordre avec pytest-socket, qui patche lui aussi `socket.socket.connect`, n'est pas fixé.
- **Scénario :** le test e2e CLI active le garde. Le test suivant, dans un autre fichier, démarre le faux moteur, puis un test du téléchargement simulé en local plante plus loin avec `ConnexionInterdite`. Le résultat dépend de l'ordre des tests. Sur l'EliteBook, avec un proxy Wavestone configuré, 100 % des fiches partent en repli.
- **Correction (AD-9 resserré) :**

> - API : `activer(hotes: list[str]) -> None` (idempotente ; résout chaque nom en IP au moment de l'activation par `getaddrinfo`, conserve noms et IP), `desactiver() -> None` (restaure les fonctions sauvegardées à l'activation), `@contextmanager garde(hotes)`, et `tentatives() -> list[tuple[str, int]]` (toutes les tentatives refusées depuis l'activation).
> - `ConnexionInterdite` hérite d'`ErreurWaveAudit` et **pas** d'`OSError`. Les adaptateurs la laissent passer sans la convertir, et le lot ne la rattrape pas (code CLI 4).
> - Ordre dans `fiches`, `ui` et `banc` : `charger_configuration()` (lecture locale seulement), puis `with garde(config.reseau.hotes_autorises):` qui englobe **tout** le reste de la commande. Aucun import d'adaptateur au niveau module avant cela.
> - `interfaces/web/app.py` expose `creer_app(config) -> FastAPI`, qui n'active pas le garde. La commande `ui` active le garde puis appelle `uvicorn.run(creer_app(config), host=config.ui.hote, port=…)`. `test_hors_ligne` entoure explicitement le parcours `TestClient` de `garde(...)`.
> - Tout client `httpx` du runtime est créé avec `trust_env=False`.
> - Le garde s'active après pytest-socket (activé à la collecte) et se désactive avant lui (LIFO).

### E4. Propriétaire du cycle de vie de llama-server, PID pour le banc, et ambiguïtés du manifeste

- **Unités :** `adaptateurs/llama_server.py`, `application/composition.py`, `application/lot.py`, `interfaces/web/app.py`, `application/banc.py` et `installation/manifeste.py`.
- **Trous :**
  1. Qui entre dans le gestionnaire de contexte ? Si c'est le lot, l'UI recharge 1 Go de poids à chaque lot. Si c'est l'UI au démarrage, la CLI et l'UI ont deux chemins différents.
  2. Le banc doit lire le RSS de llama-server, mais rien ne lui donne le PID.
  3. `chemin(role)` est ambigu : il y a deux candidats de rôle `candidat`, et `--modele <nom>` désigne un nom, pas un rôle.
  4. `prefixe_systeme` « vient du manifeste », mais `workflows/` ne peut pas importer `installation`. Et en `externe` il n'y a pas d'entrée de manifeste.
  5. Pour le zip du moteur, on ne sait pas si `destination` désigne un dossier ou un fichier, ni où se trouve `llama-server.exe`.
  6. Le format TOML (`[[artefact]]` ou `[artefacts.<nom>]`) n'est pas fixé.
  7. L'URL GitHub du zip n'est pas dans la table Stack, qui ne donne que les URL Hugging Face.
- **Scénario :** l'agent du banc lance son propre `psutil.process_iter()` et cherche `llama-server.exe` par nom. Il trouve le llama-server d'un autre lot UI. L'agent de l'installation écrit `[[artefacts]]` alors que la socle lit `[[artefact]]`, d'où une `KeyError`.
- **Correction (AD-11 et AD-12 resserrés) :**

> - `application/composition.py` expose `@contextmanager ouvrir(config: Configuration, modele: str | None) -> Iterator[tuple[Ports, InfoMoteur]]`, avec `InfoMoteur(nom_modele: str, pid: int | None, base_url: str)`. En `local-gere`, elle résout l'entrée du manifeste et démarre `LlamaServer(binaire, gguf, ctx, threads, delai)`. En `externe`, elle n'ouvre aucun processus.
> - **`executer_lot` appelle `composition.ouvrir`, une fois par lot** (un llama-server par lot, y compris dans l'UI : coût de chargement accepté pour le POC). Elle publie `pid_moteur` dans `lot_demarre.details`. Le banc est un abonné : il lit le PID dans cet événement et échantillonne dans son propre thread jusqu'à `lot_termine` ou `lot_echoue`.
> - `config/artefacts.toml` : un tableau `[[artefact]]` aux champs exacts d'AD-12, plus `executable` (chemin relatif dans `destination`, pour le rôle `moteur` seulement). `destination` est un chemin relatif à `var/` : un dossier si `extraire = true`, sinon le fichier final.
> - API de `installation/manifeste.py` : `charger(chemin) -> list[Artefact]`, `par_nom(nom) -> Artefact`, `par_role(role) -> Artefact` (lève une erreur si le rôle n'est pas unique), `chemin(artefact) -> Path` (l'exécutable pour le moteur).
> - `prefixe_systeme` est résolu par la composition (manifeste en `local-gere`, `config.moteur.prefixe_systeme` en `externe`) et passé dans `Ports.prefixe_systeme`.
> - URL du moteur : `https://github.com/ggml-org/llama.cpp/releases/download/b11714/llama-b11714-bin-win-cpu-x64.zip` (à confirmer par la socle).

### E5. Faux moteur : une fixture paramétrée impossible, un timeout non borné et un bloc `<constat>` au contenu non fixé

- **Unités :** `tests/conftest.py`, `tests/faux_moteur.py`, `workflows/fiches/prompt.py` et les tests de chaque story.
- **Trous :**
  - Une fixture pytest ne se paramètre pas par un argument (`faux_moteur(scenario=…)`). Il faut une fabrique, d'autant que CAP-9 exige deux endpoints dans le même test.
  - `lent` dépasse un timeout de 180 s par défaut, d'où des tests de plusieurs minutes.
  - Le contenu JSON de `<constat>` n'est pas fixé : le faux moteur doit en tirer les rubriques et convertir `cvss_vecteur` en métriques.
  - On ne sait pas dans quel message (système ou utilisateur) se trouvent les balises, ni si le corps d'une note XSS peut contenir `<constat>`.
  - Le compteur de `json_invalide_une_fois` n'est pas défini, ni `var` en test (les tests écriraient dans le `var/` du dépôt, et des worktrees parallèles se marcheraient dessus).
- **Scénario :** la story CLI écrit `@pytest.mark.parametrize("faux_moteur", ["lent"], indirect=True)`. La story moteur écrit `faux_moteur("lent")`, en appelant la fixture. L'une des deux ne tourne pas. Le prompt sérialise `ConstatType.model_dump()` complet, références comprises, et le faux moteur recopie tout dans `description`, ce qui fait passer `references_inventees` pour « nominal ».
- **Correction (AD-10 resserré) :**

> - `faux_moteur` est une fixture **fabrique** : `faux_moteur(scenario: str = "nominal") -> FauxMoteur`, avec `FauxMoteur(base_url: str, requetes: list[dict])` et `base_url = "http://127.0.0.1:<port>/v1"`. Chaque appel démarre un serveur ; tous sont arrêtés au teardown (`server.should_exit = True`, `join(5)`).
> - Fixture `config_test(tmp_path, base_url) -> Configuration` : `mode="externe"`, `timeout_s=1.0`, `chemins.var = tmp_path / "var"`. Tous les tests passent par elle.
> - `lent` attend 3 s avant de répondre. `json_invalide_une_fois` renvoie du non-JSON au **premier** `POST /v1/chat/completions` de ce serveur, puis du nominal. `injoignable` donne une `base_url` vers un port libre fermé, sans serveur. `erreur_500` répond 500 à chaque génération (`/v1/models` reste à 200).
> - Le prompt place dans le **dernier message `user`**, dans cet ordre : `<constat>` + `json.dumps(constat.model_dump(include={"id","titre","description","impact","recommandation","cvss_vecteur"}), ensure_ascii=False)` + `</constat>`, puis `<note>…</note>`. Le faux moteur prend la **première** occurrence de `<constat>`.
> - `references_inventees` ajoute `CWE-9999`, `CVE-2099-0001` et `https://exemple.invalid/x` à la description.
> - `domaine/cvss31.py` fournit `metriques_depuis_vecteur(vecteur) -> MetriquesCvss`, que le faux moteur réutilise.

### E6. UI : 409 non atomique, noms de fichiers déposés non assainis, état partagé entre threads, échec invisible

- **Unités :** `interfaces/web/app.py` (route `POST /lots`, thread de lot, route `/etat`) et `application/lot.py`.
- **Trous :**
  - Le test « un lot tourne-t-il ? » et le démarrage ne sont pas atomiques : deux POST simultanés dans le threadpool de FastAPI lancent deux lots.
  - Les fichiers sont-ils écrits avant le 409 ?
  - Les noms déposés ne sont pas assainis : `..\..\x.md`, `CON.md`, `A.md` et `a.md` (collision sous NTFS), `desktop.ini`.
  - La liste d'événements est mutée par le thread du lot et lue par les requêtes, sans verrou.
  - Le JSON de `/etat` n'est pas défini, ni l'état « échoué ».
  - On ne sait pas ce que renvoie `rapport.docx` avant la fin.
- **Scénario :** le JS du gabarit attend `{"evenements": [...], "etat": "termine"}`, la route renvoie une liste nue. Ou bien la sonde échoue, le thread meurt sans libérer le verrou, et toute l'UI répond 409 jusqu'au redémarrage.
- **Correction (Rule de l'UI, à ajouter au spine) :**

> - Un `threading.Lock` est acquis en non bloquant **avant** toute écriture. S'il est déjà pris : HTTP 409, et rien n'est écrit. Il est relâché dans un `finally` du thread de lot.
> - Noms déposés : `Path(nom).name` doit correspondre à `^[A-Za-z0-9][A-Za-z0-9 ._-]{0,99}\.(md|txt)$` (insensible à la casse). Les noms réservés Windows (`CON`, `PRN`, `AUX`, `NUL`, `COM1-9`, `LPT1-9`) sont refusés, ainsi que les doublons insensibles à la casse. Taille maximale de 1 Mo par fichier. Tout refus donne HTTP 400 avec un message, sans lancer de lot.
> - État d'un lot, protégé par un verrou et copié à la lecture : `GET /lots/{id}/etat` renvoie `{"id_lot": str, "etat": "en_cours"|"termine"|"echoue", "evenements": [EvenementLot…], "erreur": str|None}`.
> - `GET /lots/{id}/rapport.docx` : 404 si le lot est inconnu, 409 s'il n'est pas `termine`.
> - Le thread de lot est `daemon=True`.

### E7. Le port `SourceNotes` et le parsing des notes ne sont pas définis (encodage Windows compris)

- **Unités :** `adaptateurs/notes_fichiers.py`, `workflows/fiches/pipeline.py` (étape `lire`), les notes de démonstration et `interfaces/web/app.py` (dépôt).
- **Trous :**
  - On ne sait pas qui lit le fichier ni qui parse l'en-tête : l'étape `lire` du pipeline, ou l'adaptateur ?
  - Ni comment une note invalide est représentée (exception ou valeur).
  - Le BOM UTF-8 du Bloc-notes fait échouer la détection de `---`, et les fins de ligne CRLF aussi (`---\r`).
  - Les extensions ne sont pas fixées : `.MD`, `.markdown` ? Et `Thumbs.db` ?
  - L'ordre de tri n'est pas dit (sensible à la casse ou non), ni s'il faut descendre dans les sous-dossiers.
  - On ne sait pas quoi faire d'une clé inconnue, ni d'une `severite_pressentie` hors liste (invalide, ou ignorée ?).
- **Scénario :** un testeur écrit sa note dans le Bloc-notes (BOM, CRLF). L'en-tête n'est pas reconnu et le YAML part dans le corps, donc dans la requête BM25 avec `constat_attendu: WEB-XSS-REFLECHI` : fuite de l'étiquette, et un score de banc artificiellement parfait. Ou bien un agent lève `EntreeInvalide` pour une seule note, ce qui interrompt tout le lot (code 2).
- **Correction (nouvelle Rule, CAP-1) :**

> - `SourceNotes.lire(dossier: Path) -> list[Note | NoteInvalide]`. Elle lit les fichiers `*.md` et `*.txt` (extension insensible à la casse), sans descendre dans les sous-dossiers, en ignorant tout autre fichier. Le résultat est trié par `fichier.casefold()`. Elle lève `EntreeInvalide` seulement si le dossier est absent ou s'il ne contient aucun `.md` ni `.txt`.
> - Lecture en `encoding="utf-8-sig"`, puis normalisation `\r\n` vers `\n`. Un en-tête n'existe que si la première ligne vaut exactement `---`. Il se termine à la ligne `---` suivante et doit être un mapping YAML (sinon `NoteInvalide`).
> - Une clé inconnue est ignorée (avec un log). Une `severite_pressentie` hors liste devient `None` (avec un log). Une erreur d'encodage donne `NoteInvalide`.
> - L'étape `lire` du pipeline ne fait aucune entrée-sortie : elle reçoit une `Note` ou une `NoteInvalide` déjà construite.
> - La requête BM25 = `(note.titre or "") + "\n" + note.corps`, jamais `constat_attendu` ni `actif`.

---

## Moyen

### M1. BM25 : la variante d'IDF et la pondération des champs changent le classement et le seuil `non_rattachee`

- **Unités :** `domaine/recherche.py` et AD-6 (« score du premier candidat égal à 0 »). La réussite de CAP-3 (18/20 et 15/20) en dépend.
- **Trou :** l'IDF de Robertson `log((N-n+0,5)/(n+0,5))` devient négatif pour un terme présent dans plus de la moitié des constats. Le score peut alors être négatif, et le test « égal à 0 » ne détecte plus les notes hors sujet. « Poids ×3 » peut se lire de trois façons : BM25F, somme pondérée de trois BM25, ou répétition des jetons.
- **Correction :**

> - IDF = `ln(1 + (N - n + 0,5) / (n + 0,5))`, toujours positif.
> - Document indexé = `titre` répété 3 fois, puis `mots_cles` (joints par des espaces) répétés 3 fois, puis `description` une fois, tokenisés en une seule suite. `avgdl` est calculé sur ces longueurs. Un seul BM25 classique.
> - `non_rattachee` si le score maximal est `<= 0.0`, c'est-à-dire si aucun jeton de la requête n'est dans le vocabulaire.
> - Signature : `classer(constats: list[ConstatType], requete: str, *, k1: float, b: float) -> list[Candidat]`, triée par score décroissant puis par `id` croissant.

### M2. Garde-fous : la casse, la ponctuation et la forme canonique des identifiants de référence ne sont pas fixées

- **Trou :** si le modèle écrit `cwe-79`, l'expression régulière sensible à la casse le laisse passer. `https://owasp.org/x).` capture la parenthèse et le point, donc l'URL ne correspond plus à celle du catalogue et elle est retirée à tort. On ne sait pas si le catalogue écrit `A03:2021` ou `OWASP-A03`, ce qui rend le motif inutile. Retirer un jeton laisse des espaces doubles et des parenthèses vides.
- **Correction :**

> - Les motifs s'appliquent avec `re.IGNORECASE`. La comparaison se fait en majuscules pour les identifiants. Pour les URL, on retire d'abord la ponctuation finale `.,;:)]}>"'`, puis on compare à l'égalité exacte.
> - Les références du catalogue utilisent ces formes canoniques : `CWE-79`, `CAPEC-63`, `WSTG-INPV-01`, `A03:2021`, CVE en majuscules. `catalogue verifier` refuse un `id` de référence qui n'a pas la forme canonique de son motif (sauf pour les guides ANSSI, dont l'URL suffit).
> - Après un retrait, on normalise les espaces multiples et on supprime les `()` et `[]` vides.
> - Un motif `reference_retiree` est créé par jeton retiré, avec le jeton dans `detail`.
> - Le titre est une rubrique textuelle soumise aux étapes 2 et 4.

### M3. CVSS : deux propriétaires possibles (`domaine/cvss31.py` et `garde_fous.py`) et une sévérité non localisée

- **Trou :** la Structural Seed crée `cvss31.py`, alors qu'AD-5 appelle `cvss.CVSS3` dans les garde-fous. La bibliothèque `cvss` renvoie des sévérités en anglais (`High`), tandis que les notes utilisent `elevee`. Rien n'interdit au catalogue des vecteurs avec des métriques temporelles, ni un ordre différent.
- **Correction :**

> - `domaine/cvss31.py` est le seul à importer `cvss`. Il expose `vecteur(m: MetriquesCvss) -> str` (ordre canonique `AV/AC/PR/UI/S/C/I/A`), `metriques_depuis_vecteur(v) -> MetriquesCvss` (lève `EntreeInvalide`) et `evaluer(v) -> Cvss`.
> - Correspondance des sévérités : `None` → `aucune`, `Low` → `faible`, `Medium` → `moyenne`, `High` → `elevee`, `Critical` → `critique`. Le libellé affiché dans le rapport est « Aucune », « Faible », « Moyenne », « Élevée » ou « Critique ».
> - `cvss_vecteur` du catalogue = exactement les 8 métriques de base, préfixées par `CVSS:3.1/`. `catalogue verifier` le contrôle.

### M4. Pièges Windows non couverts

- **Sortie de llama-server :** avec `stdout=PIPE` non lu, le tampon se remplit et le processus se bloque au milieu d'un lot. Correction : rediriger vers `var/journaux/llama-server-<id_lot>.log` et passer `creationflags=CREATE_NO_WINDOW`. Pour l'arrêt : `terminate()`, puis `wait(5)`, puis `kill()`, puis fermeture du handle du Job Object. Assignation par `AssignProcessToJobObject(job, int(proc._handle))` juste après `Popen`.
- **`localhost` contre `127.0.0.1` :** sous Windows, `localhost` se résout d'abord en `::1`. Si le serveur n'écoute que sur `127.0.0.1`, il faut attendre environ 2 s de refus avant le repli. Rule : toute `base_url` générée utilise `127.0.0.1`, jamais `localhost`.
- **Port libre :** le schéma « bind sur le port 0, fermeture, passage du port » laisse une fenêtre de course. Rule : un seul nouvel essai sur un autre port si `/health` ne répond pas et que le processus s'est arrêté.
- **Console :** la console Windows en cp850 ou cp1252 ne sait pas encoder « — ». Un `typer.echo` du bandeau lève `UnicodeEncodeError`, et le code retour est faux. Rule : `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` (et de même pour `stderr`) au début de `main()`.
- **Rapport ouvert dans Word :** `-o rapport.docx` échoue avec `PermissionError`. Rule : message clair et code 4, en conservant `var/sorties/<id>/rapport.docx`.
- **Fuite de chemin :** la traçabilité et le journal ne contiennent que des noms de fichiers, jamais `C:\Users\<nom>\…` (qui révèle l'identité du consultant dans un rapport livrable).

### M5. Débordement du contexte (`-c 4096`)

- **Trou :** un corps de note avec une longue sortie d'outil, plus le constat, plus le schéma, plus `max_tokens`, dépasse 4096 jetons. llama-server répond 400, et on ne sait pas si c'est un repli ou une `SortieInvalide`.
- **Correction :** le prompt tronque le corps à `moteur.taille_max_note` caractères, en ajoutant `[…tronqué]` et un motif `rubrique_completee` (ou un code dédié `note_tronquee`, qu'il faudrait alors ajouter à `CodeMotif` dans la socle). Un HTTP 400 relève de `MoteurInjoignable` (E1 et C8), donc d'un repli.

### M6. Codes retour et options de la CLI incomplets

- `ConfigurationInvalide` et `ConnexionInterdite` n'ont pas de code. Rule : `ConfigurationInvalide` → 2, `ConnexionInterdite` → 4, toute exception non `ErreurWaveAudit` → 4 avec la trace dans `logging`, sans trace sur la console.
- `--modele` en mode `externe` : il surcharge `moteur.modele_api`. En `local-gere`, un nom absent du manifeste donne le code 2.
- `waveaudit catalogue verifier` : code 0 si le catalogue est valide, 2 sinon, avec une ligne par erreur (`fichier:id: message`).

### M7. Exporteur : format de `theme.toml`, textes exacts des rubriques et signature

- **Trou :** le test de CAP-6 cherche « les cinq rubriques » et « à revoir » par leur texte, mais ces textes ne sont pas figés. Le format de `theme.toml` est inconnu.
- **Correction :**

> - Signature : `Exporteur.exporter(rapport: Rapport, chemin: Path) -> None`.
> - Intitulés exacts (niveau 3) : `Description`, `Impact`, `Recommandation`, `CVSS 3.1`, `Références`, `Statut`, `Traçabilité`.
> - Libellé de statut : `À revoir`, suivi des motifs en liste (`code : detail`). Bandeau exact : `Démonstration — données fictives`.
> - Annexe : un titre de niveau 1 `Annexe — notes écartées`, puis un tableau `Note | Statut | Motif`.
> - `theme.toml` : `couleur_primaire = "#RRGGBB"`, `couleur_secondaire = "#RRGGBB"`, `logo = "logo.png"` (relatif à `theme-prive/`), toutes clés facultatives. Une clé inconnue est ignorée.
> - Le test de thème privé crée son `theme-prive/` sous `tmp_path`, via `config.chemins.theme_prive`.

### M8. UI locale exposée au CSRF et au DNS rebinding

- **Trou :** n'importe quelle page ouverte dans le navigateur peut faire `POST http://127.0.0.1:8765/lots`. L'enjeu est faible pour un POC sur des données fictives, mais ce sera un point de revue PASSI.
- **Correction (facultative pour le POC) :** refuser toute requête dont l'en-tête `Host` n'est pas `127.0.0.1:<port>` ou `localhost:<port>` (contre le DNS rebinding), et toute requête `POST` dont l'en-tête `Origin` est présent et différent de cette valeur.

---

## Points où un agent seul serait bloqué ou obligé de deviner

1. **Les types partagés et la configuration** (C2, C4, C7, E2) : tout agent hors de la socle devra inventer `Fiche`, `Configuration`, `RequeteLot` et `EvenementLot`. Sans AD-0, il n'y a pas d'ordre d'exécution qui le résolve.
2. **Les ports `Catalogue`, `SourceNotes`, `Exporteur`** : ils n'ont aucune signature. Proposition de `Catalogue` : `constats() -> list[ConstatType]` (triés par id, ids uniques) et `obtenir(id) -> ConstatType` (lève `EntreeInvalide`). `CatalogueYaml(dossier: Path)` lit `*.yaml` en UTF-8, dont la racine est une liste YAML. Une erreur donne `ConfigurationInvalide`, avec le fichier et l'index.
3. **Le type `Message`** n'est défini nulle part. Proposition : `class Message(TypedDict): role: Literal["system","user"]; content: str`, dans `domaine/ports.py`.
4. **L'URL de llama.cpp** et le contenu du zip (`llama-server.exe` à la racine ?) : à vérifier par la socle. L'agent installation ne peut pas le savoir hors ligne.
5. **Le comportement de `--jinja` avec `response_format.json_schema`** sur Granite 4.0 et MiniCPM5 : il n'est vérifiable qu'avec le vrai moteur (test `slow`). Il faut le noter comme un risque, pas comme une hypothèse.
6. **Les noms exacts du binaire de la commande SBOM** : `cyclonedx-py environment --output-format JSON --output-file var/sbom.cdx.json <sys.executable>`. Il faut préciser qu'on passe l'interpréteur du venv (`sys.executable`) et `subprocess.run(..., check=True)`, sinon il analyse le Python global, absent du poste.
7. **Le format de `banc.json`** n'est pas défini. Proposition : `{"id_lot", "modele", "fiches": [{"note", "duree_s"}], "duree_mediane_s", "duree_max_s", "pic_rss_app_o", "pic_rss_moteur_o", "pic_rss_total_o", "top1": int, "top3": int, "etiquetees": int}`. Les champs `top1` et `top3` sont calculés depuis `tracabilite` et `EntreeEcartee`, en comparant `constat_attendu` aux candidats.
8. **`installer` :** on ne sait pas s'il faut un fichier temporaire `.part` puis un renommage, ni ce qui se passe pour un fichier présent avec une mauvaise empreinte. Proposition : téléchargement dans `<destination>.part`, vérification de la taille puis du SHA-256, puis renommage. Un fichier existant avec une mauvaise empreinte est supprimé, puis retéléchargé une fois. Pour le test, la source est `file://` ou `httpx.MockTransport` (sans réseau, CAP-10). Il faut préciser lequel, sinon l'agent installation et le reviewer divergent.

## Ordre d'exécution recommandé pour la nuit

1. **socle** (AD-0), seule, intégrée et vérifiée (`git log -1` et suite complète verte), avant tout le reste.
2. En parallèle : `recherche` (BM25), `garde_fous` + `cvss31`, `catalogue` (contenu + adaptateur + `verifier`), `notes` (adaptateur + 20 notes de démo, avec la liste C5), `moteur_openai`, `garde_reseau`, `installation`, `export_docx`.
3. Puis : `pipeline fiches` + `prompt`, puis `lot` + `composition` + `llama_server`.
4. Puis : `cli`, `ui`, `banc`, et enfin `test_hors_ligne` (e2e).

Les étapes 3 et 4 dépendent des signatures de l'étape 2 : sans AD-0, il ne faut pas les lancer en parallèle de l'étape 2.
