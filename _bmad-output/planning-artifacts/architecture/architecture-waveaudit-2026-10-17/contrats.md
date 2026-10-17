# Contrats exacts — WaveAudit POC

Annexe normative de `ARCHITECTURE-SPINE.md`. La story `socle` (AD-0) transcrit ce fichier en code. Les autres stories l'appliquent sans en modifier les formes. Un écart nécessaire s'arrête et se signale.

## 1. Modèles partagés — `domaine/modeles.py`

Tous en `model_config = ConfigDict(extra="forbid", frozen=True)`.

```python
class Statut(StrEnum): OK="ok"; A_REVOIR="a_revoir"; NON_TRAITEE="non_traitee"; NON_RATTACHEE="non_rattachee"
class Reference(BaseModel): id: str; titre: str; url: str
class ConstatType(BaseModel):
    id: str; titre: str; famille: Literal["web","ad","infra","config","crypto","autre"]
    mots_cles: list[str]; description: str; impact: str; recommandation: str
    cvss_vecteur: str            # "CVSS:3.1/" + exactement les 8 métriques de base, ordre AV/AC/PR/UI/S/C/I/A
    references: list[Reference]  # au moins 1
    source: str                  # origine et licence
class Note(BaseModel):
    fichier: str                 # nom de fichier seul, jamais un chemin
    titre: str | None; actif: str | None
    severite_pressentie: Literal["critique","elevee","moyenne","faible","info"] | None
    constat_attendu: str | None  # transporté jusqu'à la traçabilité ; jamais lu par la recherche ni le prompt
    corps: str                   # non vide après strip
class NoteInvalide(BaseModel): fichier: str; raison: str
class MetriquesCvss(BaseModel):
    AV: Literal["N","A","L","P"]; AC: Literal["L","H"]; PR: Literal["N","L","H"]; UI: Literal["N","R"]
    S: Literal["U","C"]; C: Literal["N","L","H"]; I: Literal["N","L","H"]; A: Literal["N","L","H"]
class Cvss(BaseModel): vecteur: str; score: float; severite: Literal["aucune","faible","moyenne","elevee","critique"]
class CodeMotif(StrEnum):
    REFERENCE_RETIREE="reference_retiree"; VECTEUR_INVALIDE="vecteur_invalide"; RUBRIQUE_COMPLETEE="rubrique_completee"
    NOTE_TRONQUEE="note_tronquee"; REPLI_SORTIE_INVALIDE="repli_sortie_invalide"; REPLI_MOTEUR="repli_moteur"
    NOTE_INVALIDE="note_invalide"; AUCUN_CONSTAT="aucun_constat"
class Motif(BaseModel): code: CodeMotif; detail: str
class Candidat(BaseModel): id: str; score: float
class Tracabilite(BaseModel): note: str; constat_id: str; candidats: list[Candidat]; constat_attendu: str | None
class Fiche(BaseModel):
    titre: str; description: str; impact: str; recommandation: str
    cvss: Cvss; references: list[Reference]
    statut: Literal[Statut.OK, Statut.A_REVOIR]; motifs: list[Motif]   # a_revoir <=> motifs non vide
    tracabilite: Tracabilite
class EntreeEcartee(BaseModel):
    note: str; statut: Literal[Statut.NON_TRAITEE, Statut.NON_RATTACHEE]
    motif: Motif; candidats: list[Candidat]; constat_attendu: str | None
ResultatElement = Fiche | EntreeEcartee
class Rapport(BaseModel): fiches: list[Fiche]; ecartees: list[EntreeEcartee]
class TypeEvenement(StrEnum):
    LOT_DEMARRE="lot_demarre"; FICHE_DEMARREE="fiche_demarree"; FICHE_TERMINEE="fiche_terminee"
    FICHE_NON_TRAITEE="fiche_non_traitee"; FICHE_NON_RATTACHEE="fiche_non_rattachee"
    LOT_TERMINE="lot_termine"; LOT_ECHOUE="lot_echoue"
class EvenementLot(BaseModel):
    type: TypeEvenement; horodatage: AwareDatetime  # datetime.now().astimezone() ; un datetime naïf est refusé
    index: int | None                             # 1..total pour les événements de fiche, None sinon
    total: int; note: str | None                  # nom de fichier
    statut: Statut | None; duree_s: float | None
    details: dict[str, str | int | float | None] = {}
class RequeteLot(BaseModel):
    dossier: Path; workflow: str = "fiches"
    modele: str | None = None          # surcharge moteur.modele (local-gere) ou moteur.modele_api (externe)
    id_lot: str | None = None          # None : généré par le lot
    copie_rapport: Path | None = None  # -o : copie de rapport.docx en plus de var/sorties/<id>/
class ResultatLot(BaseModel):
    id_lot: str; dossier_sortie: Path; rapport: Rapport; chemin_rapport: Path; duree_s: float
def schema_sortie(longueur_max: int) -> dict
```

`schema_sortie` renvoie le JSON Schema envoyé au moteur, sans `$ref` ni `$defs` et avec `additionalProperties: false` à chaque niveau : `titre`, `description`, `impact`, `recommandation` (`string`, `minLength` 1, `maxLength` = `longueur_max`) et `cvss` (objet des 8 métriques en enum). Tous les champs sont requis. Aucun champ de références.

Sérialisation de `fiches.json` : `Rapport.model_dump(mode="json")`, c'est-à-dire `{"fiches": [...], "ecartees": [...]}`.

`EvenementLot.details` :
- `lot_demarre` : `{"id_lot", "modele", "pid_moteur"}` (`pid_moteur` vaut `None` en externe) ;
- `lot_echoue` : `{"erreur": <nom de classe>, "message"}`.

## 2. Configuration — `domaine/configuration.py` (modèle), `application/config.py` (chargement)

Toutes les sections sont en `extra="forbid"`. `config/waveaudit.toml` contient exactement :

```toml
[moteur]
mode = "local-gere"          # "local-gere" | "externe"
base_url = ""                # externe : URL complète finissant par /v1, ex. "http://127.0.0.1:8080/v1"
modele = ""                  # nom d'une entrée du manifeste ; vide = choix auto défaut/repli
modele_api = ""              # champ "model" envoyé ; vide = nom de l'entrée du manifeste
prefixe_systeme = ""         # externe seulement ; en local-gere il vient du manifeste
cle_api = ""                 # vide = pas d'en-tête Authorization
timeout_s = 180.0
temperature = 0.2
seed = 42
max_tokens = 700
longueur_max_rubrique = 1200
taille_max_note = 6000       # caractères du corps envoyés au modèle
ctx = 4096
threads = 4
ram_min_defaut_go = 4.5
delai_demarrage_s = 120.0
[reseau]
hotes_autorises = ["127.0.0.1", "::1", "localhost"]
[recherche]
k1 = 1.5
b = 0.75
[chemins]                    # relatifs à racine_projet()
var = "var"
catalogue = "donnees/catalogue"
theme_prive = "theme-prive"
manifeste = "config/artefacts.toml"
[ui]
hote = "127.0.0.1"
port = 8765
```

API de `application/config.py` :
- `racine_projet() -> Path` : le dossier qui contient `config/waveaudit.toml`, résolu depuis l'emplacement du paquet ;
- `charger_configuration(chemin: Path | None = None) -> Configuration` : fusion profonde des défauts, de `racine_projet()/waveaudit.local.toml` s'il existe, puis de `chemin`. Une erreur lève `ConfigurationInvalide`.

Tout chemin relatif se résout contre `racine_projet()`, jamais contre `cwd`. Un chemin absolu, en test sous `tmp_path`, est accepté tel quel.

## 3. Ports — `domaine/ports.py`

```python
class Message(TypedDict): role: Literal["system","user"]; content: str
class Moteur(Protocol):
    def sonder(self) -> None: ...                 # GET {base_url}/models ; statut != 200 -> MoteurInjoignable
    def generer_json(self, messages: list[Message], schema: dict, *, max_tokens: int) -> dict: ...
class Catalogue(Protocol):
    def constats(self) -> list[ConstatType]: ...  # triés par id, ids uniques
    def obtenir(self, id: str) -> ConstatType: ... # EntreeInvalide si absent
class SourceNotes(Protocol):
    def lire(self, dossier: Path) -> list[Note | NoteInvalide]: ...
class Exporteur(Protocol):
    def exporter(self, rapport: Rapport, chemin: Path) -> None: ...
class MesureMemoire(Protocol):
    def rss_octets(self, pid: int) -> int | None: ...  # None si le processus n'existe plus
@dataclass(frozen=True)
class Ports:
    moteur: Moteur; catalogue: Catalogue; source_notes: SourceNotes; exporteur: Exporteur; prefixe_systeme: str
@dataclass(frozen=True)
class InfoMoteur: nom_modele: str; pid: int | None; base_url: str
```

Sémantique de `generer_json` (`adaptateurs/moteur_openai.py`) :
- `POST {base_url}/chat/completions` avec `{"model", "messages", "temperature", "seed", "max_tokens", "response_format": {"type": "json_schema", "json_schema": {"name": "sortie_fiche", "strict": true, "schema": schema}}}`. llama-server ignore `strict` ; le champ est envoyé pour les endpoints compatibles qui l'appliquent.
- Il lève `SortieInvalide` **seulement** si `choices[0].message.content` n'est pas du JSON ou si ce n'est pas un objet. Il ne valide pas le schéma.
- Il lève `MoteurInjoignable` sur une connexion refusée, un timeout (`timeout_s`) ou tout statut HTTP différent de 200 (400 et 500 compris).
- Le client `httpx.Client(trust_env=False, timeout=timeout_s)` envoie l'en-tête `Authorization: Bearer <cle_api>` seulement si `cle_api` n'est pas vide.

## 4. Erreurs — `domaine/erreurs.py`

`ErreurWaveAudit(Exception)` → `EntreeInvalide`, `ConfigurationInvalide`, `MoteurInjoignable`, `SortieInvalide`, `ConnexionInterdite`, `EmpreinteInvalide`. Aucune n'hérite d'`OSError`.

| Exception | Code CLI |
|---|---|
| aucune (lot terminé, même avec des `a_revoir`) | 0 |
| `EntreeInvalide`, `ConfigurationInvalide`, `--modele` inconnu, `catalogue verifier` en échec | 2 |
| `MoteurInjoignable` (sonde initiale) | 3 |
| `ConnexionInterdite`, `PermissionError` sur `-o`, toute autre exception | 4 |
| `EmpreinteInvalide` | 5 |

La CLI affiche un message d'une ligne en français, sans trace ; la trace va dans `logging`.

## 5. Workflow — `workflows/registre.py`

```python
class Workflow(Protocol):
    def preparer(self, dossier: Path) -> list[Note | NoteInvalide]: ...    # via ports.source_notes
    def traiter(self, element: Note | NoteInvalide) -> ResultatElement: ... # aucune E/S, aucun événement
    def assembler(self, resultats: list[ResultatElement]) -> Rapport: ...
REGISTRE: dict[str, Callable[[Configuration, Ports], Workflow]] = {"fiches": workflows.fiches.pipeline.creer}
```

Pipeline `fiches.traiter(element)` :
1. `NoteInvalide` → `EntreeEcartee(non_traitee, motif note_invalide)`.
2. `classer(...)` (§7) → score maximal `<= 0` → `EntreeEcartee(non_rattachee, motif aucun_constat)`, sans appel au modèle.
3. `prompt.construire(note, constat, prefixe_systeme, taille_max_note) -> list[Message]` (§8).
4. `generer_json`. Le workflow vérifie la présence des 4 rubriques (chaînes) ; sinon il lève `SortieInvalide`. `SortieInvalide` → un seul nouvel essai, puis un repli avec le motif `repli_sortie_invalide`. `MoteurInjoignable` → repli immédiat avec le motif `repli_moteur`.
5. `garde_fous.appliquer(sortie_brute: dict, constat, note, candidats, longueur_max) -> Fiche`. Le repli passe aussi par là, avec une sortie construite depuis le constat type et le motif de repli.

## 6. Garde-fous — `domaine/garde_fous.py`, `domaine/cvss31.py`

- `cvss31.py` est le seul module qui importe `cvss`. Il expose :
  - `vecteur(m: MetriquesCvss) -> str` ;
  - `metriques_depuis_vecteur(v: str) -> MetriquesCvss` (lève `EntreeInvalide`) ;
  - `evaluer(v: str) -> Cvss`, via `cvss.CVSS3(v)`, `scores()[0]` et `severities()[0]`. Il rattrape `CVSS3MalformedError` et `CVSS3MandatoryError` pour lever `EntreeInvalide`.
  - Correspondance des sévérités : `None` → `aucune`, `Low` → `faible`, `Medium` → `moyenne`, `High` → `elevee`, `Critical` → `critique`.
- Ordre d'`appliquer` :
  1. `references` = celles du constat type.
  2. Retrait des références inventées : sur les rubriques `titre`, `description`, `impact` et `recommandation`, `re.IGNORECASE`, avec les motifs `CWE-\d+`, `CVE-\d{4}-\d+`, `CAPEC-\d+`, `WSTG-[A-Z]+-\d+`, `A\d{2}:20\d{2}`, `ANSSI-[A-Z0-9-]+`, `CERTFR-\d{4}-[A-Z]{3}-\d{3}` et `https?://\S+`.
     - Identifiants comparés en majuscules aux `id` des références du constat type.
     - URL comparées à l'égalité exacte aux `url`, après retrait de la ponctuation finale `.,;:)]}>"'`.
     - Chaque jeton absent est retiré et donne un motif `reference_retiree` (le jeton dans `detail`). On normalise ensuite les espaces et on supprime les `()` et `[]` vides.
  3. Métriques : métrique absente ou hors enum → vecteur par défaut du constat type, motif `vecteur_invalide`. Sinon `evaluer(vecteur(m))`.
  4. Une rubrique vide ou de moins de 20 caractères après nettoyage reçoit le texte du constat type, avec le motif `rubrique_completee`. Une rubrique de plus de `longueur_max` caractères est tronquée.
  5. `statut = a_revoir` si et seulement si `motifs` n'est pas vide.

## 7. Recherche — `domaine/recherche.py`

`classer(constats: list[ConstatType], requete: str, *, k1: float, b: float) -> list[Candidat]`

Tri par score décroissant, puis par `id` croissant ; la fonction renvoie tous les constats, et le workflow garde les 3 premiers.

- **Tokenisation :** minuscules, NFKD sans diacritiques, découpage sur `[^a-z0-9]+`, jetons d'au moins 2 caractères, mots vides français et anglais d'une liste figée dans le module.
- **Document indexé :** `titre` ×3, puis `" ".join(mots_cles)` ×3, puis `description` ×1, concaténés en une seule suite de jetons. `avgdl` est calculé sur ces documents.
- **IDF :** `ln(1 + (N - n + 0.5) / (n + 0.5))`. Le score est le BM25 classique.
- **Requête :** `(note.titre or "") + "\n" + note.corps`, jamais `constat_attendu` ni `actif`.
- Non rattachée si score maximal `<= 0.0`.

## 8. Prompt — `workflows/fiches/prompt.py`

- `[system]` : `prefixe_systeme` (s'il n'est pas vide) suivi de la consigne en français. La consigne demande :
  - d'adapter le constat type aux observations de la note, sans inventer d'identifiant, de référence, d'URL ni de fait absent de la note ;
  - de garder le vecteur par défaut sauf si la note le contredit ;
  - de répondre en JSON conforme.
- `[user]`, dans cet ordre :
  - `<constat>` + `json.dumps(constat.model_dump(include={"id","titre","description","impact","recommandation","cvss_vecteur"}), ensure_ascii=False)` + `</constat>` ;
  - puis `<note>` + l'actif s'il existe (`Actif : …`) + le corps tronqué à `taille_max_note`, suivi de `[…tronqué]` en cas de troncature + `</note>`.
- Une troncature ajoute le motif `note_tronquee`. Le pipeline le transmet aux garde-fous par `appliquer(..., motifs_initiaux=[...])`.

## 9. Lot et composition — `application/lot.py`, `application/composition.py`

- `composition.ouvrir(config: Configuration, modele: str | None) -> ContextManager[tuple[Ports, InfoMoteur]]`.
  - En `local-gere`, il résout l'entrée du manifeste (`modele`, sinon `config.moteur.modele`, sinon `modele_defaut`, ou `modele_repli` si la RAM disponible est sous `ram_min_defaut_go`), puis démarre `LlamaServer`.
  - En `externe`, il utilise `base_url` et n'ouvre aucun processus.
  - `prefixe_systeme` vient de l'entrée du manifeste en `local-gere`, de `config.moteur.prefixe_systeme` en `externe`.
- `composition.creer_mesure_memoire() -> MesureMemoire` (adaptateur `memoire_psutil`) : seul accès du banc à la mesure mémoire.
- `nouvel_id_lot(var: Path) -> str` renvoie `AAAAMMJJ-HHMMSS`, avec un suffixe `-2`, `-3`… si besoin. Il crée `var/sorties/<id>/` par `mkdir(exist_ok=False)` et réessaie en cas de collision.
- `executer_lot(requete, config, abonne) -> ResultatLot` :
  1. Crée le dossier de sortie.
  2. Ouvre la composition **une fois par lot**, puis appelle `ports.moteur.sonder()`. En cas d'échec : événement `lot_echoue`, puis l'exception remonte.
  3. Émet `lot_demarre`.
  4. Pour chaque élément, émet `fiche_demarree`, chronomètre `traiter`, puis émet `fiche_terminee`, `fiche_non_traitee` ou `fiche_non_rattachee`.
  5. Appelle `assembler`, écrit `fiches.json`, appelle `exporter` vers `rapport.docx`, copie vers `copie_rapport` s'il est donné, puis émet `lot_termine`.
- **Seul `lot.py` écrit `journal.jsonl`** (`model_dump_json()`, une ligne par événement, flush), avant d'appeler l'abonné. Une exception de l'abonné est journalisée et ignorée.
- Seules `EntreeInvalide`, `ConfigurationInvalide`, `MoteurInjoignable` (sonde) et `ConnexionInterdite` sortent d'`executer_lot`.
- Traçabilité et journal : noms de fichiers seulement, jamais de chemin absolu.

## 10. llama-server — `adaptateurs/llama_server.py`

`LlamaServer(binaire: Path, gguf: Path, ctx: int, threads: int, delai_s: float, journal: Path)` est un gestionnaire de contexte qui expose `base_url` (`http://127.0.0.1:<p>/v1`) et `pid`.

- **Port :** bind sur `127.0.0.1:0`, lecture du port, fermeture.
- **Lancement :** `Popen([binaire, "-m", gguf, "--host", "127.0.0.1", "--port", p, "-c", ctx, "-t", threads, "--parallel", "1", "--no-webui", "--jinja"], stdout=journal, stderr=STDOUT, creationflags=CREATE_NO_WINDOW)`. Le journal est `var/journaux/llama-server-<id_lot>.log`.
- **Job Object :** Windows uniquement, par `ctypes` : `CreateJobObjectW`, puis `SetInformationJobObject(JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE)`, puis `OpenProcess(PROCESS_SET_QUOTA | PROCESS_TERMINATE, False, pid)`, puis `AssignProcessToJobObject`. On n'utilise pas `Popen._handle`.
- **Attente :** `GET http://127.0.0.1:<p>/health` = 200 dans `delai_s`. Si le processus meurt pendant l'attente, un seul nouvel essai sur un autre port. Sinon, `MoteurInjoignable`.
- **Arrêt :** `terminate()`, puis `wait(5)`, puis `kill()`, puis fermeture des handles.
- Toute `base_url` générée utilise `127.0.0.1`, jamais `localhost`.

## 11. Manifeste — `config/artefacts.toml`, `installation/`

Un tableau `[[artefact]]` aux champs `nom, role, version, url, sha256, taille, licence, source, destination, extraire, executable, prefixe_systeme`.
- `destination` est relatif à `var/` : un dossier si `extraire = true`, sinon le fichier final.
- `executable` est le chemin de l'exécutable dans `destination`, pour le rôle `moteur` seulement.

| nom | role | url | prefixe_systeme |
|---|---|---|---|
| `llama-server-b11714` | moteur | `https://github.com/ggml-org/llama.cpp/releases/download/b11714/llama-b11714-bin-win-cpu-x64.zip` (`extraire = true`, `destination = "moteur/b11714"`, `executable` à confirmer en ouvrant le zip à l'installation : `llama-server.exe`) | |
| `granite-4.0-1b-q4km` | modele_defaut | `https://huggingface.co/ibm-granite/granite-4.0-1b-GGUF/resolve/b27c2fe3f211b7f44e80fa620177aea371099aaa/granite-4.0-1b-Q4_K_M.gguf` | |
| `minicpm5-1b-q4km` | modele_repli | `https://huggingface.co/openbmb/MiniCPM5-1B-GGUF/resolve/3d55fac80935ae6456986ad2384b5cbcc4d6c948/MiniCPM5-1B-Q4_K_M.gguf` | |
| `qwen3-1.7b-q4km` | candidat | `https://huggingface.co/unsloth/Qwen3-1.7B-GGUF/resolve/d7f544eead698dbd1f15126ef60b45a1e1933222/Qwen3-1.7B-Q4_K_M.gguf` | `/no_think` |
| `qwen3.5-0.8b-q4km` | candidat | `https://huggingface.co/unsloth/Qwen3.5-0.8B-GGUF/resolve/6ab461498e2023f6e3c1baea90a8f0fe38ab64d0/Qwen3.5-0.8B-Q4_K_M.gguf` | |

Les tailles et les SHA-256 sont dans la table Stack du spine. Les modèles ont `destination = "modeles/<fichier>"`.

API de `installation/manifeste.py` :
- `charger(chemin) -> list[Artefact]` ;
- `par_nom(nom)` ;
- `par_role(role)` (erreur si le rôle n'est pas unique) ;
- `chemin(artefact, var: Path) -> Path` (l'exécutable pour le moteur).

`installation/telechargement.py` :
- Il télécharge par `httpx` (`trust_env=True` autorisé ici seulement, pour le proxy d'entreprise) vers `<destination>.part`, vérifie la taille puis le SHA-256, puis renomme.
- Un fichier final déjà présent avec la bonne empreinte est sauté. Avec une mauvaise empreinte, il est supprimé et retéléchargé une fois.
- En cas d'écart après téléchargement : suppression, puis `EmpreinteInvalide`.
- Il accepte un `transport: httpx.BaseTransport | None`. Les tests passent un `httpx.MockTransport`, sans réseau.

`installation/sbom.py` : `subprocess.run([sys.executable, "-m", "cyclonedx_py", "environment", "--output-format", "JSON", "--output-file", <var>/sbom.cdx.json, sys.executable], check=True)`.

## 12. Garde réseau — `securite/garde_reseau.py`

- `activer(hotes: list[str])` :
  - idempotente ;
  - résout chaque nom par `getaddrinfo` ;
  - sauvegarde puis remplace `socket.socket.connect`, `socket.socket.connect_ex` et `socket.create_connection` ;
  - lève `ConnexionInterdite` vers une IP hors liste, et l'enregistre.
- `desactiver()` restaure les fonctions sauvegardées.
- `@contextmanager garde(hotes)`.
- `tentatives() -> list[tuple[str, int]]`.
- **Ordre dans les commandes `fiches`, `ui` et `banc` :** `charger_configuration()` d'abord, puis `with garde(config.reseau.hotes_autorises):` autour de tout le reste. Aucun import d'adaptateur au niveau module de `cli.py`.
- **Tests :**
  - `addopts` contient `--allow-hosts=127.0.0.1,::1`, et **jamais** `--disable-socket` (bogue pytest-socket n° 540 avec les serveurs en thread).
  - Le garde s'active après pytest-socket et se désactive avant lui.

## 13. Faux moteur — `tests/faux_moteur.py`, `tests/conftest.py`

- La fixture **fabrique** `faux_moteur(scenario: str = "nominal") -> FauxMoteur`, avec `FauxMoteur(base_url: str, requetes: list[dict])` et `base_url = "http://127.0.0.1:<port>/v1"`. Chaque appel démarre un serveur uvicorn dans un thread ; tous sont arrêtés au teardown (`should_exit = True`, `join(5)`).
- Routes : `GET /health`, `GET /v1/models` (toujours 200, sauf `injoignable`), `POST /v1/chat/completions`.
- **Scénario `nominal` :**
  - il lit la première occurrence de `<constat>…</constat>` dans le dernier message `user` ;
  - il renvoie `"[adapté] " + rubrique` pour les 4 rubriques et `metriques_depuis_vecteur(cvss_vecteur)` ;
  - le tout dans `choices[0].message.content` (chaîne JSON).
- **Autres scénarios :**

| Scénario | Comportement |
|---|---|
| `json_invalide` | toujours `"pas du json"` |
| `json_invalide_une_fois` | non-JSON au premier POST de ce serveur, puis nominal |
| `references_inventees` | nominal, avec `CWE-9999`, `CVE-2099-0001` et `https://exemple.invalid/x` ajoutés à la description |
| `vecteur_invalide` | nominal, avec `"AV": "X"` |
| `lent` | attend 3 s avant de répondre |
| `erreur_500` | 500 sur chaque POST |
| `injoignable` | `base_url` vers un port libre fermé, sans serveur |

- La fixture `config_test(tmp_path, faux_moteur)` renvoie une `Configuration` avec `mode="externe"`, la `base_url` du faux moteur, `timeout_s=1.0` et `chemins.var = tmp_path / "var"`. Le catalogue est celui du dépôt, sauf surcharge. Tous les tests passent par elle et n'écrivent jamais dans le `var/` du dépôt.

## 14. Notes sur disque — `adaptateurs/notes_fichiers.py`

- **Sélection :** `*.md` et `*.txt` (extension insensible à la casse), sans descendre dans les sous-dossiers, en ignorant tout autre fichier ; tri par `casefold()`. `EntreeInvalide` seulement si le dossier est absent ou s'il ne contient aucune note.
- **Lecture :** `encoding="utf-8-sig"`, puis `\r\n` → `\n`.
- **En-tête :** il existe seulement si la première ligne vaut exactement `---`. Il se termine à la ligne `---` suivante et doit être un mapping YAML.
- **`NoteInvalide` :** YAML illisible, en-tête qui n'est pas un mapping, corps vide ou erreur d'encodage.
- **Tolérance :** une clé inconnue est ignorée (log). Une `severite_pressentie` hors liste devient `None` (log).

## 15. Catalogue — `adaptateurs/catalogue_yaml.py`, `waveaudit catalogue verifier`

- **Lecture :** `CatalogueYaml(dossier)` lit `<famille>.yaml` (UTF-8, racine = liste YAML). Toute erreur lève `ConfigurationInvalide`, en citant le fichier et l'index.
- **`verifier` contrôle :**
  - le schéma `ConstatType` ;
  - l'unicité des `id` dans tout le catalogue ;
  - un préfixe d'`id` égal à la famille et au fichier (`WEB-` dans `web.yaml`) ;
  - un `cvss_vecteur` égal aux 8 métriques de base au format canonique et évaluable ;
  - au moins une référence ;
  - des références `id` de forme canonique (`CWE-79`, `CAPEC-63`, `WSTG-INPV-01`, `A03:2021`, `ANSSI-<SIGLE>`, `CERTFR-AAAA-XXX-NNN`) et `url` en `https://` ;
  - la présence des 35 identifiants figés (§16) ;
  - un total d'au moins 30 constats.
- **Sortie :** code 0 si tout est valide, sinon code 2 avec une ligne par erreur (`fichier:id: message`).

## 16. Identifiants figés

- **Catalogue (au moins ces 35, d'autres peuvent s'ajouter) :**
  - **web :** `WEB-XSS-REFLECHI`, `WEB-XSS-STOCKE`, `WEB-INJECTION-SQL`, `WEB-CSRF`, `WEB-IDOR`, `WEB-SSRF`, `WEB-TRAVERSEE-CHEMIN`, `WEB-UPLOAD-NON-RESTREINT`, `WEB-SESSION-FIXATION`, `WEB-ENTETES-SECURITE`, `WEB-CORS-PERMISSIF`, `WEB-REDIRECTION-OUVERTE`, `WEB-DIVULGATION-ERREURS`, `WEB-AUTH-FORCE-BRUTE`, `WEB-XXE`, `WEB-DESERIALISATION` ;
  - **ad :** `AD-KERBEROASTING`, `AD-ASREP-ROASTING`, `AD-DELEGATION-NON-CONTRAINTE`, `AD-LAPS-ABSENT`, `AD-ADMINS-EXCESSIFS`, `AD-GPP-MOT-DE-PASSE` ;
  - **infra :** `INFRA-SMB-SIGNATURE`, `INFRA-SERVICE-OBSOLETE`, `INFRA-SNMP-COMMUNAUTE`, `INFRA-RDP-EXPOSE`, `INFRA-LLMNR-NBTNS` ;
  - **config :** `CONFIG-MOT-DE-PASSE-DEFAUT`, `CONFIG-SECRETS-EN-CLAIR`, `CONFIG-LISTAGE-REPERTOIRE`, `CONFIG-DEBUG-ACTIF` ;
  - **crypto :** `CRYPTO-TLS-OBSOLETE`, `CRYPTO-CERTIFICAT-INVALIDE`, `CRYPTO-HACHAGE-FAIBLE` ;
  - **autre :** `AUTRE-JOURNALISATION-INSUFFISANTE`.
- **Notes de démonstration 01 à 20 :**
  - 20 `constat_attendu` distincts, pris dans cette liste : au moins 3 en `ad`, 2 en `infra`, 2 en `crypto` et 2 en `config`.
  - Fichier `NN-<id en minuscules sans préfixe de famille>.md`, par exemple `01-xss-reflechi.md`.
  - Rédaction réaliste et variée : vocabulaire différent de celui du catalogue, preuves en texte (requêtes, extraits de sortie d'outil fictifs), données fictives (domaines `exemple.test` ou `*.local`, IP RFC 5737).
- **Note hors sujet :** une 21e note, `tests/donnees/notes/hors-sujet.md`, sert de test `non_rattachee` (vocabulaire sans rapport, par exemple une recette de cuisine).

## 17. Rapport Word — `adaptateurs/export_docx.py`

- **Point de départ :** `theme-prive/modele.docx` s'il existe, sinon `Document()` avec le thème générique (`theme_generique.py`).
- **`theme.toml` facultatif :** `couleur_primaire = "#RRGGBB"`, `couleur_secondaire`, `logo` (relatif à `theme-prive/`). Une clé inconnue est ignorée.
- **Bandeau exact,** en en-tête et en pied de chaque section : `Démonstration — données fictives`.
- **Structure :**
  - titre du document `Rapport de constats`, puis une table de synthèse `N° | Titre | Sévérité | Score | Statut` ;
  - puis, par fiche, un titre de niveau 2 (`N. <titre>`) et les intitulés de niveau 3, exactement : `Description`, `Impact`, `Recommandation`, `CVSS 3.1` (vecteur, score, sévérité affichée parmi `Aucune`, `Faible`, `Moyenne`, `Élevée`, `Critique`), `Références` (`id — titre — url`), `Statut` (`OK`, ou `À revoir` suivi des motifs `code : detail`), `Traçabilité` (note, constat type).
- **Annexe :** titre de niveau 1 `Annexe — notes écartées`, puis un tableau `Note | Statut | Motif`, présent seulement si `ecartees` n'est pas vide.

## 18. Interface web — `interfaces/web/`

- **Création :** `creer_app(config) -> FastAPI`, qui n'active pas le garde.
- **Démarrage :** la commande `ui` active le garde puis lance `uvicorn.run(app, host=config.ui.hote, port=config.ui.port)`. Elle refuse de démarrer (code 2) si `ui.hote` n'est pas `127.0.0.1` ou `::1`.
- **Middleware :**
  - en-tête `Host` différent de `127.0.0.1:<port>`, `localhost:<port>` ou `testserver` : HTTP 400 ;
  - `POST` dont l'en-tête `Origin` est présent et ne correspond pas : HTTP 403.
- **Pages et ressources :** chaque page affiche le bandeau. Les gabarits Jinja2 et le JS vanilla sont servis depuis `interfaces/web/static/`. Un test vérifie qu'aucun gabarit ni fichier statique ne contient `http://` ou `https://` hors de `127.0.0.1`.
- **`POST /lots` (multipart, champ `notes`, plusieurs fichiers) :**
  1. Prend un `threading.Lock` en non bloquant **avant** toute écriture. S'il est déjà pris : HTTP 409, et rien n'est écrit.
  2. Valide chaque nom : `Path(nom).name` doit correspondre à `^[A-Za-z0-9][A-Za-z0-9 ._-]{0,99}\.(md|txt)$` (insensible à la casse). Sont refusés : les noms réservés Windows, les doublons insensibles à la casse et les fichiers de plus de 1 Mo. Un refus donne HTTP 400 et libère le verrou.
  3. Appelle `nouvel_id_lot`, écrit dans `var/entrees/<id_lot>/`, lance un thread `daemon` qui exécute `executer_lot` et relâche le verrou dans un `finally`.
  4. Redirige (303) vers `/lots/<id_lot>`.
- **`GET /lots/{id}/etat` :** `{"id_lot", "etat": "en_cours"|"termine"|"echoue", "evenements": [...], "erreur": str|None}`. L'état est protégé par un verrou et copié à la lecture.
- **`GET /lots/{id}/rapport.docx` :** 404 si le lot est inconnu, 409 s'il n'est pas terminé.

## 19. CLI — `interfaces/cli.py` (typer)

- **Au début de `main()` :** `sys.stdout.reconfigure(encoding="utf-8", errors="replace")`, et de même pour `stderr`.
- **Commandes :** `installer [--candidats]`, `fiches DOSSIER [-o FICHIER] [--modele NOM] [--config F]`, `ui [--port N] [--config F]`, `catalogue verifier`, `banc DOSSIER [--modele NOM]`, `sbom`.
- **Sortie de `fiches` :**
  - une ligne par événement de fiche (`[3/20] 03-injection-sql.md : ok (95 s)`) ;
  - puis la synthèse : le nombre de fiches `ok` et `a_revoir`, le nombre d'entrées écartées, le chemin du rapport ;
  - le bandeau `Démonstration — données fictives`, en première et en dernière ligne.
- `--modele` en `externe` surcharge `modele_api`. En `local-gere`, un nom absent du manifeste donne le code 2.

## 20. Banc — `application/banc.py`

- **Fonctionnement :** le banc est un abonné du lot. Il lit `pid_moteur` dans `lot_demarre`, puis échantillonne toutes les 0,5 s, dans son propre thread, `MesureMemoire.rss_octets` de l'application (`os.getpid()`) et du moteur, jusqu'à `lot_termine` ou `lot_echoue`.
- **`var/sorties/<id>/banc.json` :** `{"id_lot", "modele", "fiches": [{"note", "duree_s"}], "duree_mediane_s", "duree_max_s", "pic_rss_app_o", "pic_rss_moteur_o", "pic_rss_total_o", "top1", "top3", "etiquetees"}`. `top1` et `top3` sont calculés depuis `tracabilite` et `EntreeEcartee`.
- **Affichage :** un résumé lisible en console.

## 21. Workflow incident (CERT) — `domaine/incident.py`, `workflows/incident/`, `application/incident.py`

Ajouté le 2026-10-17 (SPEC-waveaudit-cert), révisé après la revue adversariale (`specs/spec-waveaudit-cert/reviews/review-adversariale.md`). C1 crée les formes, ports, constantes, fixtures et les deux extractions du socle (journal, moteur) ; C2 à C6b les appliquent sans toucher au socle. Conditions des règles, champs, chronologie de démo et oracle : `formats-incident.md` (normatif).

### Formes (`domaine/incident.py`, C1)

Toutes `ConfigDict(extra="forbid", frozen=True)`.

```python
class Evenement(BaseModel):
    source: Literal["windows","linux"]; fichier: str; ligne: int
    horodatage: AwareDatetime; hote: str
    event_id: int | None; log_name: str | None; programme: str | None
    message: str; champs: dict[str, str]
    @property
    def cle(self) -> tuple[str, int]: return (self.fichier, self.ligne)   # Evenement n'est PAS hachable
class LigneIgnoree(BaseModel): fichier: str; ligne: int; raison: str       # raison libre, non comparée
class LectureJournaux(BaseModel):
    evenements: list[Evenement]; ignorees: list[LigneIgnoree]
    fichiers: dict[str, int]          # nom -> enregistrements examinés (événements + ignorées)
class Condition(BaseModel):
    event_id: list[int] | None = None; log_name: str | None = None; programme: str | None = None
    champs: dict[str, str] = {}; champs_regex: dict[str, str] = {}; au_moins_un: dict[str, str] = {}
    message_regex: str | None = None
class Agregation(BaseModel): seuil: int; fenetre_s: int; par: list[str] = []
class Regle(BaseModel):
    id: str; titre: str; description: str; impact: str; recommandation: str
    severite: Literal["critique","elevee","moyenne","faible"]; references: list[Reference]
    source: Literal["windows","linux"]; condition: Condition; agregation: Agregation | None = None
class Indicateur(BaseModel):
    type: Literal["ip","compte","hote","hachage","executable"]; valeur: str; origines: list[str]  # "fichier:ligne"
class Detection(BaseModel):
    regle_id: str; debut: AwareDatetime; fin: AwareDatetime; hotes: list[str]
    evenements: list[Evenement]       # tous les déclencheurs, triés (horodatage, fichier casefold, ligne)
    indicateurs: list[Indicateur] = []
class Recit(BaseModel):
    detection: Detection; regle_titre: str; titre: str; recit: str; impact: str; recommandation: str
    severite: Literal["critique","elevee","moyenne","faible"]; references: list[Reference]
    statut: Literal[Statut.OK, Statut.A_REVOIR]; motifs: list[Motif]
class RapportIncident(BaseModel):
    debut: AwareDatetime | None; fin: AwareDatetime | None; recits: list[Recit]
    indicateurs: list[Indicateur]; actifs: list[str]; recommandations: list[str]
    sources: dict[str, int]; ignorees: list[LigneIgnoree]
class RequeteIncident(BaseModel): dossier: Path; annee: int; modele: str | None = None; id_lot: str | None = None; copie_rapport: Path | None = None
class ResultatIncident(BaseModel): id_lot: str; dossier_sortie: Path; rapport: RapportIncident; chemin_rapport: Path; duree_s: float
def schema_recit(longueur_max: int) -> dict   # {titre, recit, impact, recommandation} : string, minLength 1, maxLength, required, additionalProperties false
```

Validations (chacune testée par C1) :

| Forme | Validation |
|---|---|
| Evenement | `ligne >= 1` ; `fichier` nom seul (validateur de `Note.fichier`) |
| LigneIgnoree | `ligne >= 1` ; `fichier` nom seul |
| Condition | au moins un critère non vide |
| Agregation | `seuil >= 2`, `fenetre_s >= 1` |
| Regle | `id` `^INC-(WIN\|LIN)-[A-Z0-9]+(-[A-Z0-9]+)*$` ; préfixe cohérent avec `source` ; `references` ≥ 1 |
| Detection | `debut <= fin` ; `evenements` non vide |
| Indicateur | `origines` non vide |
| Recit | `statut = a_revoir` ssi `motifs` non vide (même validateur que `Fiche`) |

Constantes (C1, importées par C2 à C4, jamais redéfinies) :

| Constante | Valeur |
|---|---|
| `CHAMPS_WINDOWS`, `CHAMPS_LINUX` | frozensets des tables « Champs normalisés » de `formats-incident.md` |
| `PROGRAMMES_LINUX` | `{"sshd","sudo","useradd"}` |
| `SEVERITES` | `("critique","elevee","moyenne","faible")` (ordre d'affichage) |
| `LIBELLES_SEVERITE` | `{"critique":"Critique","elevee":"Élevée","moyenne":"Moyenne","faible":"Faible"}` |
| `TYPES_INDICATEUR` | `("compte","executable","hachage","hote","ip")` |
| `IDS_REGLES_MINIMAUX` | les 15 ids du catalogue minimal |
| `MOTIF_TECHNIQUE` | `(?<![A-Za-z0-9])T\d{4}(?:\.\d{3})?(?![\d.])`, IGNORECASE |
| `MOTIF_IPV4` | `(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])` |
| `MOTIF_IPV6` | `(?<![0-9A-Fa-f:])[0-9A-Fa-f:]*:[0-9A-Fa-f:]*:[0-9A-Fa-f:.]*` (candidat ; validé par `ipaddress`) |
| `MOTIF_HACHAGE` | `(?<![0-9A-Fa-f])(?:[0-9A-Fa-f]{64}\|[0-9A-Fa-f]{40}\|[0-9A-Fa-f]{32})(?![0-9A-Fa-f])` |

(`\|` = barre verticale échappée pour le tableau.) C1 ajoute à `CodeMotif` (socle) `INDICATEUR_RETIRE = "indicateur_retire"`, et rien d'autre ; les autres codes sont réutilisés.

### Configuration (C1)

```toml
[chemins]
regles = "donnees/regles"      # ConfigChemins.regles: Path = Path("donnees/regles"), résolu comme les autres chemins
[incident]                      # ConfigIncident, extra="forbid"
decalage_syslog = "+02:00"     # fixe, sans heure d'été ; motif ^[+-]\d{2}:\d{2}$
max_preuves = 10               # >= 1 ; preuves citées dans le prompt et le rapport
longueur_max_recit = 800       # >= 100 ; maxLength de chaque rubrique
max_tokens = 1000              # >= 100 ; passé à generer_json pour le récit
```

`application/config.py` et `config_test` ne changent pas (`[chemins]` y est déjà résolu). `moteur.mode_json`, s'il a été ajouté par V1 (§22), est conservé tel quel.

### Ports (`domaine/ports.py`, C1)

```python
class SourceJournaux(Protocol):
    def lire(self, dossier: Path, *, annee: int) -> LectureJournaux: ...  # EntreeInvalide si dossier absent ou sans fichier routé
class CatalogueRegles(Protocol):
    def regles(self) -> list[Regle]: ...    # triées par id
class ExporteurIncident(Protocol):
    def exporter(self, rapport: RapportIncident, chemin: Path) -> None: ...
@dataclass(frozen=True)
class PortsIncident:                         # aucun processus, aucune connexion
    source_journaux: SourceJournaux; regles: CatalogueRegles; exporteur: ExporteurIncident
```

### Composition et journal

| Fonction | Story | Contrat |
|---|---|---|
| `composition.ouvrir_moteur_incident(config, modele) -> ContextManager[tuple[Moteur, str, InfoMoteur]]` | C1 | (moteur, prefixe_systeme, info) ; même résolution et même cycle de vie que `ouvrir` (§9), extraits dans une fonction privée commune ; `ouvrir` inchangé (`tests/e2e/test_lot.py` vert) |
| `application/journal.py` : `JournalLot(chemin: Path)`, `ecrire(evenement: EvenementLot) -> None` | C1 | extrait de `lot.py` sans changement de comportement (`model_dump_json()`, une ligne, flush) ; seul écrivain de `journal.jsonl`, utilisé par `lot.py` et `incident.py` (AD-8 s'entend ainsi) |
| `composition.creer_ports_incident(config) -> PortsIncident` | C5 | **ajout** d'une fonction, sans modifier l'existant ; instancie `SourceJournauxFichiers`, `CatalogueReglesYaml(config.chemins.regles)` et l'exporteur de C6a |

### Lecture (C2) — `adaptateurs/journaux_windows.py`, `journaux_linux.py`, `journaux.py` (`SourceJournauxFichiers`)

- Fichiers du dossier, sans sous-dossiers ni fichiers cachés, triés par `nom.casefold()`. Routage insensible à la casse : suffixe `.json`/`.csv` → Windows ; nom `auth.log*`, `syslog*`, `secure*` ou suffixe `.log` → Linux ; suffixe `.gz`, `.zip`, `.bz2`, `.xz` et tout autre fichier : ignoré en silence. Aucun fichier routé → `EntreeInvalide`.
- `Evenement.fichier` = nom seul. Correspondance des champs et normalisation des valeurs : `formats-incident.md`.
- Encodage : BOM UTF-16 (`FF FE` ou `FE FF`) → `utf-16` ; sinon `utf-8-sig` (Windows) ou `utf-8` `errors="replace"` (syslog).
- JSON : racine tableau, sinon (ou JSON invalide) une seule `LigneIgnoree(ligne=1)`. `ligne` = rang 1-based de l'objet. Élément non objet, sans `TimeCreated` ISO avec fuseau, sans `Id` entier ou sans `MachineName` : `LigneIgnoree` à ce rang.
- CSV : `newline=""` ; séparateur `;` si l'en-tête en contient plus que de `,`. En-tête sans `TimeCreated`, `Id` ou `MachineName` : une `LigneIgnoree(ligne=1)`. `ligne` = ligne physique où **commence** l'enregistrement (en-tête = 1). Enregistrement vide sauté.
- Syslog : `\r` final retiré ; ligne vide sautée et non comptée. Motif `^(?P<mois>[A-Z][a-z]{2}) {1,2}(?P<jour>\d{1,2}) (?P<heure>\d{2}:\d{2}:\d{2}) (?P<hote>\S+) (?P<prog>[^\s:\[]+)(?:\[\d+\])?: ?(?P<message>.*)$`, mois par table anglaise fixe (jamais `strptime("%b")`), date impossible (29 févr. non bissextile) → `LigneIgnoree`. Une ligne commençant par un ISO 8601 avec fuseau suivi de ` hote prog[pid]: message` est acceptée avec son année et son fuseau. Sinon année = `annee`, fuseau = `decalage_syslog` ; dans un même fichier, un mois inférieur à celui de la ligne acceptée précédente incrémente l'année (jamais de décrément).
- Toute ligne non reconnue donne une `LigneIgnoree`, jamais une exception. Événements triés par `(horodatage, fichier.casefold(), ligne)`.

### Détection (C3) — `domaine/detection.py`, `detecter(regles, evenements) -> list[Detection]`

- Applicabilité : une règle ne s'applique qu'aux événements de même `source`. Critères : `event_id` (appartenance), `log_name` et `programme` (égalité `casefold`), `champs` (clé présente ET valeur égale en `casefold`), `champs_regex` (clé présente ET `re.search`), `au_moins_un` (au moins une clé présente dont la valeur vérifie `re.search`), `message_regex` (`re.search`). Clé absente = critère faux. Regex en `re.IGNORECASE`.
- `correspond(regle, evenement) -> bool`, public : applicabilité seule (source et critères), sans agrégation.
- Sans agrégation : une détection par événement ; `debut = fin = horodatage`, `hotes = [hote]`.
- Avec agrégation : on garde les événements qui ont TOUS les champs `par` (les autres sont écartés de la règle), groupés par le tuple des valeurs en `casefold` (`par: []` = un seul groupe). Dans chaque groupe, événements triés par `(horodatage, fichier.casefold(), ligne)`, indices 0..n-1, `t` en secondes ; « dans la fenêtre » = `t_k - t_j <= fenetre_s` (borne incluse) :

```text
i = 0
tant que i < n :
    k = plus petit indice >= i tel que #{j : i <= j <= k et t_k - t_j <= fenetre_s} >= seuil
    si aucun k : arrêter
    d = plus petit j >= i tel que t_k - t_j <= fenetre_s
    f = k
    tant que f + 1 < n et #{j : d <= j <= f+1 et t_{f+1} - t_j <= fenetre_s} >= seuil : f += 1
    détection : evenements = groupe[d..f], debut = t_d, fin = t_f,
                hotes = sorted({e.hote}, key=str.casefold)
    i = f + 1
```

- Vecteurs de test obligatoires : seuil 3, fenêtre 60 : `t = 0,10,20,100,110,120` → 2 détections [0..20] et [100..120] ; `t = 0,10,70,80,90` → 1 détection [70..90] (0 et 10 perdus) ; `t = 0,30,60` → 1 (borne incluse) ; `t = 0,30,61` → aucune. Seuil 5, fenêtre 300 : 8 événements toutes les 60 s → 1 détection de 8 (0 → 420). Un événement sans le champ `par` n'est compté dans aucun groupe.
- `detecter` laisse `indicateurs = []` et n'importe pas `domaine.indicateurs`.
- Tri final : `(debut, regle_id, evenements[0].fichier.casefold(), evenements[0].ligne)`.

### Règles (C3) — `adaptateurs/regles_yaml.py`

- `CatalogueReglesYaml(dossier)` : charge au constructeur chaque `*.yaml` du dossier (trié), chacun une liste ; `Regle.model_validate` puis `verifier_regles`. Toute erreur → `ConfigurationInvalide` listant toutes les erreurs (code 2).
- `verifier_regles(regles) -> list[str]` : ids uniques ; `IDS_REGLES_MINIMAUX` tous présents ; regex compilables ; clés de `champs`, `champs_regex`, `au_moins_un`, `agregation.par` dans `CHAMPS_<source>` ; `programme` dans `PROGRAMMES_LINUX` ; URL `^https://attack\.mitre\.org/techniques/T\d{4}(/\d{3})?/$` cohérente avec l'id (`T1110.001` → `/T1110/001/`) ; textes types sans jeton `MOTIF_TECHNIQUE`, `MOTIF_IPV4`, IPv6 validée ni `MOTIF_HACHAGE` ; `description`, `impact`, `recommandation` ≥ 20 caractères, `titre` non vide.

### Indicateurs (C4) — `domaine/indicateurs.py`, `extraire(evenements) -> list[Indicateur]`

- Sources, normalisation et exclusions : table de `formats-incident.md`. IPv4 de `message` par `MOTIF_IPV4` puis `ipaddress.ip_address` ; IP = `str(ipaddress.ip_address(v))`, IPv4 mappée (`::ffff:a.b.c.d`) → IPv4.
- Comptes : comparés en `casefold` après `strip` pour l'exclusion et le dédoublonnage ; on garde la graphie du premier événement dans l'ordre `(horodatage, fichier.casefold(), ligne)`.
- `origines` : `f"{fichier}:{ligne}"` distinctes, triées par `(fichier.casefold(), ligne)` numérique.
- Résultat trié par `(type, valeur)`.
- Union pour le rapport : événements dédoublonnés par `Evenement.cle`.

### Garde-fous (C4) — `domaine/garde_fous_incident.py`

`appliquer_recit(sortie_brute: dict, regle: Regle, detection: Detection, longueur_max: int, motifs_initiaux=()) -> Recit` ; `detection.indicateurs` doit être rempli avant l'appel. `regle_titre = regle.titre`.

1. `references` = celles de la règle.
2. Rubriques `titre`, `recit`, `impact`, `recommandation` : chaque jeton `MOTIF_TECHNIQUE` gardé si `upper()` est l'id d'une référence de la règle (égalité exacte : T1110 ≠ T1110.001), sinon retiré, un motif `reference_retiree` par jeton (jeton dans `detail`).
3. Jetons `MOTIF_IPV4`, `MOTIF_IPV6` et `MOTIF_HACHAGE` : un candidat qui n'est pas une IP valide (`ipaddress`) est laissé tel quel ; une IP ou un hachage est gardé si sa forme normalisée (minuscules, IPv4 mappée → IPv4) est la valeur d'un indicateur de la détection, sinon retiré (`indicateur_retire`, jeton dans `detail`). Candidats IPv6 traités d'abord : une IPv4 incluse dans une IPv6 valide (`::ffff:192.0.2.10`) n'est pas traitée une seconde fois.
4. Après retrait : espaces consécutifs réduits à un, `()` et `[]` vides supprimés.
5. Rubrique `recit`, `impact` ou `recommandation` vide ou de moins de 20 caractères → texte type de la règle (`rubrique_completee`) ; `titre` remplacé par `regle.titre` seulement s'il est vide. Troncature à `longueur_max`.
6. `statut = a_revoir` ssi `motifs` non vide.

- Repli : `{titre, recit, impact, recommandation}` = `{titre, description, impact, recommandation}` de la règle, passés à `appliquer_recit` avec `motifs_initiaux=[repli_sortie_invalide | repli_moteur]`.
- La troncature des preuves à `max_preuves` n'est pas un motif.
- Vecteurs de non-mutilation obligatoires (conservés tels quels) : `08:02:10`, `2026-10-14T08:02:10+02:00`, `10.0.17763.1`, `0x1010`, `T1110.001` si la règle l'a.

### Prompt et pipeline (C5) — `workflows/incident/prompt.py`, `pipeline.py`

- Message système : `prefixe_systeme` + consigne en français. Dernier message `user` : `<regle>` + `json.dumps({id, titre, description, impact, recommandation}, ensure_ascii=False)` + `</regle>`, puis `<preuves>` + au plus `max_preuves` lignes `f"{e.horodatage.isoformat(timespec='seconds')} {e.hote} {' '.join(e.message.split())[:300]}"` + `</preuves>`.
- `traiter_detection` : `detection.model_copy(update={"indicateurs": extraire(detection.evenements)})`, puis `generer_json(messages, schema_recit(longueur_max_recit), max_tokens=config.incident.max_tokens)` et `appliquer_recit`. `SortieInvalide` → un nouvel essai puis repli ; `MoteurInjoignable` → repli immédiat.
- `assembler_rapport(lecture, recits) -> RapportIncident` : `debut`/`fin` = min des `debut` / max des `fin` (`None` sans détection) ; `recits` dans l'ordre des détections ; `indicateurs = extraire(union)` ; `actifs` = hôtes distincts de toutes les détections, `sorted(key=str.casefold)` ; `recommandations` = `recommandation` **type** de chaque règle, ordre des détections, dédoublonnées à l'égalité ; `sources = lecture.fichiers` ; `ignorees = lecture.ignorees`.

### Faux moteur, mode incident (C1, `tests/faux_moteur.py`)

Mode incident : `<regle>` présente, `<constat>` absente. `SCENARIOS` inchangé.

| Scénario | Comportement |
|---|---|
| `nominal` | `{titre, recit, impact, recommandation}` = `"[adapté] "` + `{titre, description, impact, recommandation}` de la règle ; aucune clé `cvss` |
| `references_inventees` | nominal, avec `REFERENCES_INVENTEES_INCIDENT = " T9999 T1110.999 203.0.113.254 " + "0f" * 32` ajouté à `recit` ; attendu après garde-fous : 2 `reference_retiree` (T9999, T1110.999) et 2 `indicateur_retire` (IP, hachage), soit une IP, un hachage et une technique inventés (CAP-5) |
| `vecteur_invalide` | identique à `nominal` |
| `json_invalide`, `json_invalide_une_fois`, `lent`, `erreur_500`, `injoignable` | inchangés |
| ni `<regle>` ni `<constat>` | `SANS_CONSTAT` (inchangé) |

### Service (C5) — `application/incident.py`, `executer_incident(requete, config, abonne) -> ResultatIncident`

1. `nouvel_id_lot`, puis `ports = creer_ports_incident(config)` ; lecture (`annee = requete.annee`) et `detecter`. Aucune ouverture du moteur à ce stade.
2. S'il y a au moins une détection : `ouvrir_moteur_incident`, puis `sonder()` ; échec → `lot_echoue` puis `MoteurInjoignable` remonte (code 3).
3. Événements via `JournalLot`, sans nouveau `TypeEvenement` : `lot_demarre` (`total` = nombre de détections, `details = {"workflow": "incident"}` + `pid_moteur` s'il existe), puis par détection `fiche_demarree` et `fiche_terminee` (`note` = `regle_id`, `statut` ok/a_revoir), puis `lot_termine` ; `lot_echoue` en cas d'erreur sortante.
4. `assembler_rapport`, écriture de `incident.json` (= `RapportIncident.model_dump_json(indent=2)`) et de `rapport-incident.docx` dans `var/sorties/<id_lot>/`, copie vers `copie_rapport` s'il est donné.
- Sans détection : rapport « Aucun fait détecté », aucun appel au modèle ni ouverture du moteur (même avec un moteur injoignable : code 0).
- Seules `EntreeInvalide`, `ConfigurationInvalide`, `MoteurInjoignable` (sonde) et `ConnexionInterdite` sortent.
- Déterminisme : deux exécutions donnent un `incident.json` identique octet pour octet.

### Rapport Word (C6a) — `adaptateurs/export_incident_docx.py`

Sections, intitulés et mise en forme : `formats-incident.md` « Rapport d'incident ». Ne lit qu'un `RapportIncident`. Bandeau : réutiliser la fonction ou la constante publique d'`export_docx.py` ; s'il n'y en a pas, recopier le texte du bandeau sans modifier `export_docx.py` et le consigner dans la revue.

### CLI (C6b)

`waveaudit incident DOSSIER [-o FICHIER] [--annee N] [--modele NOM] [--config F]`, ajoutée à `interfaces/cli.py` sans modifier les autres commandes, sous le garde réseau, avec les codes retour et la forme de sortie console de `fiches`. `--annee` vaut l'année courante par défaut ; aucun test n'en dépend (toujours `--annee 2026`). `-o` vers un fichier verrouillé (`PermissionError`) → code 4.

### Limites connues (README, C6b)

- `decalage_syslog` fixe, sans heure d'été : pour un incident à cheval sur un changement d'heure, lancer deux analyses. Pas de `zoneinfo` (dépendance `tzdata` sous Windows).
- Exports Windows : le README fournit le script PowerShell d'export au format normalisé (`[xml]$_.ToXml()` vers `Data`, `TimeCreated.ToString("o")`) ; `ConvertTo-Json` brut de PowerShell 5.1 ne donne ni `Data` ni un `TimeCreated` ISO.

## 22. Mode JSON du moteur (validation sur le vrai SLM)

Ajouté le 2026-10-17.

Si le test réel montre que `response_format` en `json_schema` échoue avec un modèle (grammaire refusée, sortie vide ou non conforme), la story V1 ajoute deux réglages :
- `moteur.mode_json` à la configuration, qui vaut `"json_schema"` (défaut) ou `"json_object"` ;
- un champ facultatif `mode_json` à chaque entrée du manifeste, qui prime sur la configuration.

En `json_object`, l'adaptateur envoie `response_format = {"type": "json_object"}` et ajoute le schéma, en texte, à la fin du message système. Le reste du contrat ne change pas.

Le workflow incident (§21) passe par le même adaptateur : `mode_json` s'y applique sans changement, et C1 conserve le réglage tel que V1 l'a laissé.
