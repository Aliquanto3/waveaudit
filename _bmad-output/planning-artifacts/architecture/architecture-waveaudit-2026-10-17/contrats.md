# Contrats exacts — WaveAudit POC

Annexe normative de `ARCHITECTURE-SPINE.md`. La story `socle` (AD-0) transcrit ce fichier en code. Les autres stories l'appliquent sans en modifier les formes. Un écart nécessaire s'arrête et se signale.

**Amendement v2 (2026-10-18, SPEC-waveaudit-v2).** Les ajouts et changements v2 sont marqués **[v2]** dans les sections existantes ; les écarts entérinés (`spec-waveaudit-v2/ecarts-contrat.md`) sont marqués **[entériné v2]**. Nouveaux contrats : §23 à §30. Impact par fichier et par test : `impacts-v2.md`. Les formes partagées v2 (§1, §2, §3, §23, §25) sont posées par la story de socle v2 (AD-0, AD-18) avant toute autre story v2.

**Relecture adversariale intégrée (2026-10-18, `spec-waveaudit-v2/revue-adversariale.md`).** Les corrections sont marquées **[revue <id>]** dans les sections concernées ; elles priment sur le texte v2 qu'elles précisent ou remplacent.

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

**[v2] Ajouts à `domaine/modeles.py`** (story de socle v2) :

```python
Langue = Literal["fr", "en"]
LANGUES: tuple[Langue, ...] = ("fr", "en")
class TextesConstat(BaseModel):            # extra="forbid", frozen
    titre: str; description: str; impact: str; recommandation: str   # chacun non vide après strip
class ConstatType(BaseModel):              # champs v0.1.0 inchangés (= textes français), plus :
    en: TextesConstat | None = None        # None toléré par le modèle ; refusé par CatalogueYaml et verifier (§15)
    def textes(self, langue: Langue) -> TextesConstat: ...  # "fr" : champs racine ; "en" : self.en, ValueError si None
class CodeMotif(StrEnum):                  # valeurs v0.1.0 et INDICATEUR_RETIRE inchangées, plus :
    REPETITION = "repetition"              # §6 étape 5, detail = nom de la rubrique
    LANGUE = "langue"                      # §6 étape 6, detail = "<rubrique> : mots-outils <langue>" | "<rubrique> : écriture non latine"
    LOT_INTERROMPU = "lot_interrompu"      # §25, entrée jamais traitée d'un lot échoué ou interrompu
class RequeteLot(BaseModel):               # champs v0.1.0 inchangés, plus :
    langue: Langue | None = None           # None : config.fiches.langue
```

`Fiche`, `EntreeEcartee`, `Rapport`, `EvenementLot` et `TypeEvenement` ne changent pas. `EvenementLot.details` de `lot_demarre` (fiches) devient `{"id_lot", "modele", "pid_moteur", "workflow": "fiches", "langue"}` **[v2]**.

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

**[v2] Clés ajoutées** (story de socle v2 ; `config/waveaudit.toml` et `domaine/configuration.py` en même temps). **[revue A23]** `config_test` (`tests/conftest.py`) ne change pas : il relit `config/waveaudit.toml` et hérite donc des nouvelles clés (vérifié sur le code v0.1.0).

```toml
[moteur]
mode_json = "json_schema"      # déjà livré par V1 (§22), consigné ici
repeat_penalty = 0.0           # 0.0 = non envoyé (défaut du serveur, 1.0 sur llama-server b11714) ; sinon 0 < x <= 2.0, envoyé (§3) ; le manifeste prime (§11)
[fiches]                       # ConfigFiches, extra="forbid"
langue = "fr"                  # Literal["fr","en"] ; langue des lots sans choix explicite (§23)
[ui]
inactivite_moteur_s = 300.0    # > 0 ; arrêt du moteur à la demande après cette inactivité (§24)
```

`[incident]` et `[chemins]` sont ceux du §21. Aucune autre clé.

API de `application/config.py` :
- `racine_projet() -> Path` : le dossier qui contient `config/waveaudit.toml`, résolu depuis l'emplacement du paquet ;
- `charger_configuration(chemin: Path | None = None) -> Configuration` : fusion profonde des défauts, de `racine_projet()/waveaudit.local.toml` s'il existe, puis de `chemin`. Une erreur lève `ConfigurationInvalide`.

Tout chemin relatif se résout contre `racine_projet()`, jamais contre `cwd`. Un chemin absolu, en test sous `tmp_path`, est accepté tel quel.

## 3. Ports — `domaine/ports.py`

```python
class Message(TypedDict): role: Literal["system","user"]; content: str
class Moteur(Protocol):
    def sonder(self) -> None: ...                 # GET {base_url}/models ; statut != 200 -> MoteurInjoignable
    def generer_json(self, messages: list[Message], schema: dict, *, max_tokens: int,
                     seed: int | None = None) -> dict: ...   # [v2] seed : None = seed configurée (§5)
class Catalogue(Protocol):
    def constats(self) -> list[ConstatType]: ...  # triés par id, ids uniques
    def obtenir(self, id: str) -> ConstatType: ... # EntreeInvalide si absent
class SourceNotes(Protocol):
    def lire(self, dossier: Path) -> list[Note | NoteInvalide]: ...
class Exporteur(Protocol):
    def exporter(self, rapport: Rapport, chemin: Path, options: OptionsExport = OptionsExport()) -> None: ...  # [v2] options
@dataclass(frozen=True)
class OptionsExport:                               # [v2] §27
    langue: Langue = "fr"
    mode: Literal["lot", "final", "brouillon"] = "lot"   # "lot" = rapport.docx v0.1.0, inchangé
    non_validees: frozenset[str] = frozenset()     # noms de note des fiches non validées : marquées en brouillon, listées en annexe en final ([revue A17])
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
- **[entériné v2]** Statut 200 avec une enveloppe non conforme (corps non JSON, `choices` vide ou absent, `message` absent) → `MoteurInjoignable`. `content` null ou non textuel → `SortieInvalide`.
- **[v2] `seed`** : le corps porte `seed` si l'argument est donné, sinon la seed du constructeur (`moteur.seed`).
- **[v2] `repeat_penalty`** : valeur effective = celle de l'entrée du manifeste si elle est renseignée (local-gere), sinon `moteur.repeat_penalty`. Si elle vaut `0.0`, la clé est absente du corps (corps v0.1.0 inchangé) ; sinon `"repeat_penalty": <valeur>` est ajouté au corps. Constructeur : `MoteurOpenAI(..., repeat_penalty: float = 0.0)`, passé par `composition._moteur`.
- **[entériné v2]** `reflexion` (§22) : `chat_template_kwargs = {"enable_thinking": <bool>}` ajouté seulement si l'entrée du manifeste le renseigne.
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

La CLI affiche un message d'une ligne en français, sans trace ; la trace va dans `logging`. **[entériné v2]** Aucun chemin absolu dans les messages d'erreur de la CLI (`lot.sans_chemin`, §9).

**[v2]** Ces codes ne changent pas. `waveaudit exporter` (§27) les réutilise : lot inconnu, lot incident, export final sans fiche validée → 2 ; fichier cible verrouillé (`PermissionError`, document ouvert dans Word) → 4.

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
   - **[v2] Nouvelle tentative (CAP-1)** : premier appel `generer_json(messages, schema, max_tokens=m.max_tokens)` (seed configurée) ; second appel, mêmes messages, `generer_json(messages, schema, max_tokens=m.max_tokens, seed=(config.moteur.seed + 1) % 2**32)` **[revue E40]**. Le repli après deux échecs est inchangé. Même règle dans le pipeline incident (§21, `_generer_avec_un_essai`).
5. `garde_fous.appliquer(sortie_brute: dict, constat, note, candidats, longueur_max, *, motifs_initiaux=(), langue="fr") -> Fiche` **[v2] `langue`**. Le repli passe aussi par là, avec une sortie construite depuis `constat.textes(langue)` et le motif de repli.

**[v2] Langue et régénération.** `WorkflowFiches` lit `config.fiches.langue` (le lot lui passe une configuration où cette valeur est la langue du lot, §9). Il expose en plus, hors protocole `Workflow` (le registre ne change pas) :
- `rediger(note: Note, constat_id: str, candidats: list[Candidat]) -> Fiche` : étapes 3 à 5 sur le constat `constat_id` (lu par `ports.catalogue.obtenir`), mêmes repli et garde-fous ; utilisé par `traiter` (avec `candidats[0].id`) et par la régénération (§25).

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

**[v2] Ordre révisé d'`appliquer` (CAP-3, CAP-4)** — remplace la liste ci-dessus ; « textes du constat » = `constat.textes(langue)` :

  1. `references` = celles du constat type (inchangé).
  2. Retrait des références inventées : motifs, casse et comparaison des identifiants inchangés. **URL** **[revue A20/E39]** : un jeton URL, après retrait de la ponctuation finale `.,;:)]}>"'`, est conservé s'il est égal à l'`url` d'une référence du constat **ou** s'il est égal (jeton entier, casse comprise) à l'un des jetons URL extraits de `note.corps` ou de `note.actif` par le même motif `https?://\S+` et la même recoupe de ponctuation. Un préfixe ou un fragment d'une URL de la note n'est pas conservé. Note entière, pas la version tronquée du prompt. Une URL absente de la note et du constat est retirée (`reference_retiree`), comme avant. Les identifiants (CWE…) cités par la note restent soumis à la règle v0.1.0.
  3. Métriques (inchangé).
  4. Longueur minimale après nettoyage : `titre` **5** caractères, `description`, `impact`, `recommandation` **20** caractères (constantes `LONGUEUR_MIN_TITRE = 5`, `LONGUEUR_MIN_RUBRIQUE = 20`). Une rubrique trop courte reçoit le texte du constat (`rubrique_completee`, detail = rubrique). Puis troncature à `longueur_max`.
  5. **Répétition** (nouveau, `domaine/qualite_texte.est_repetitif`), sur chaque rubrique non complétée à l'étape 4, texte final :
     - mots = `re.findall(r"\w+", texte.lower())` ; trigrammes = n-uplets de 3 mots consécutifs ;
     - `repetitif` si `len(trigrammes) >= 10` et `1 - len(set(trigrammes)) / len(trigrammes) >= 0.30` ;
     - ou si `re.search(r"(.{3,50}?)\1{4,}", texte, re.DOTALL)` trouve un motif de 3 à 50 caractères répété au moins 5 fois d'affilée (boucle sans espaces), **[revue A19/E37]** retenu seulement si le motif contient au moins une lettre, si la suite répétée (`m.group(0)`) fait au moins 40 caractères et si elle ne figure pas telle quelle dans le texte source (`note.corps` et `note.actif` ; les preuves en incident) : une charge citée (`../../../../../`, `AAAA…`, `%2e%2e…`) n'est pas une boucle ;
     - signature : `est_repetitif(texte: str, source: str = "") -> bool` ;
     - motif `repetition` (detail = rubrique) ; le texte est conservé tel quel (le consultant le voit).
     - Mesure (2026-10-18, 17 lots réels de `var/sorties/`, 264 rubriques) : les 3 rubriques dégénérées (bouclées jusqu'à 1 200 caractères) valent 0,44, 0,66 et 0,83 ; le maximum des 261 autres vaut 0,14.
  6. **Langue** (nouveau, `domaine/qualite_texte.motif_langue(texte, langue) -> str | None`) :
     - **Écriture**, sur les 4 rubriques non complétées : une lettre de catégorie `Lu`, `Ll`, `Lt` ou `Lo` dont `unicodedata.name(c, "")` ne commence pas par `LATIN`, hors `µ`, `ª` et `º`, suffit → `"<rubrique> : écriture non latine"`. **[revue E35/E36]** Les lettres de catégorie `Lm` (`ʼ`, `ˆ`) sont ignorées ; une lettre non latine présente dans le texte source (note ou preuves) est ignorée (citation).
     - **Mots-outils**, sur `description`, `impact`, `recommandation` seulement (jamais le titre) **[revue E32-E34]** : on retire d'abord les segments cités (entre `"…"`, `“…”`, `«…»` ou `` `…` ``) ; mots = `re.findall(r"(?<!\w)[^\W\d_]+(?!\w)", texte)` (un mot collé à un chiffre, comme `DES` dans `3DES`, n'est pas compté) ; les mots entièrement en capitales de 2 lettres ou plus (sigles : `IT`, `IS`, `TO`, `DES`) sont ignorés ; le reste passe en minuscules ; `n_cible` et `n_autre` = nombre de mots présents dans la liste de la langue cible et de l'autre langue ; signalé si `n_autre >= 2` et `n_autre > n_cible` → `"<rubrique> : mots-outils <autre langue>"`.
     - Listes figées dans le module (sans mots ambigus entre les deux langues : ni `a`, `an`, `as`, `on`, `or`, `en`) :
       - `MOTS_OUTILS["fr"]` = `le la les un une des du de et est sont dans pour par sur avec qui que ne pas au aux ce cette ces leur leurs il elle ils peut permet afin être son sa ses d l qu` ;
       - `MOTS_OUTILS["en"]` = `the of and is are to in for with that this which by be can could should may from it its not allows into their has have will`.
     - Un motif `langue` par rubrique signalée ; texte conservé.
     - Signature : `motif_langue(texte, langue, source: str = "") -> str | None`. Tests dédiés (Q2) : `3DES` et `IT` dans un texte anglais, citation anglaise entre guillemets dans une rubrique française, `nº` et `ʼ`, texte cyrillique cité depuis la note, `../`×5, `A`×40 et `%2e`×6 cités depuis la note → aucun motif.
     - Mesure (2026-10-18) : 0 mot-outil anglais dans les 264 rubriques françaises réelles, dans les textes du catalogue ni dans les récits français ; le récit anglais de MiniCPM5 donne 7, 5 et 3 mots-outils anglais pour 0 français ; le caractère japonais de la note 26 (MiniCPM5 puis granite, lot `20261018-020204`) est détecté.
  7. `statut = a_revoir` si et seulement si `motifs` n'est pas vide.

`domaine/qualite_texte.py` (nouveau, stdlib seule) est partagé avec les garde-fous incident (§21).

## 7. Recherche — `domaine/recherche.py`

`classer(constats: list[ConstatType], requete: str, *, k1: float, b: float) -> list[Candidat]`

Tri par score décroissant, puis par `id` croissant ; la fonction renvoie tous les constats, et le workflow garde les 3 premiers.

- **Tokenisation :** minuscules, NFKD sans diacritiques, découpage sur `[^a-z0-9]+`, jetons d'au moins 2 caractères, mots vides français et anglais d'une liste figée dans le module. **[entériné v2]** `œ`, `æ`, `ß` sont remplacés par `oe`, `ae`, `ss` avant NFKD.
- **Document indexé :** `titre` ×3, puis `" ".join(mots_cles)` ×3, puis `description` ×1, concaténés en une seule suite de jetons. `avgdl` est calculé sur ces documents.
- **[v2] Index bilingue (CAP-8)** : un seul document par constat, quelle que soit la langue du lot : `titre` fr ×3, `en.titre` ×3, `mots_cles` ×3, `description` fr ×1, `en.description` ×1 (le bloc `en` est sauté s'il vaut `None`, cas des fixtures de test). `N` = nombre de constats (pas de doublon). Les réglages de CAP-5 (mots-clés, `k1`, `b`, pondérations) se font **sur cet index bilingue**, sans regarder les notes 21 à 30 ; les pondérations restent des constantes du module.
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

**[v2] Échappement (CAP-2).** Avant troncature, `note.corps` et `note.actif` passent par `echapper(texte) -> str` :

```python
_BALISE = re.compile(r"<(?=\s*/?\s*(?:note|constat)\b)", re.IGNORECASE)
def echapper(texte: str) -> str: return _BALISE.sub("‹", texte)   # U+2039, même longueur
```

Toute balise ouvrante ou fermante `note`/`constat` (casse et espaces quelconques) perd son `<` au profit de `‹`. Le texte reste lisible et sa longueur ne change pas : la troncature et le motif `note_tronquee` sont inchangés. Le message utilisateur contient donc exactement un `<constat>`, un `</constat>`, un `<note>` et un `</note>`. Même règle dans le prompt incident pour `regle`/`preuves`, appliquée à chaque ligne de preuve (§21, décision technique v2).

**[v2] Langue (CAP-8).** Signature `construire(note, constat, prefixe_systeme, taille_max_note, *, langue: Langue = "fr") -> list[Message]`.
- `CONSIGNES: dict[Langue, str]` : `CONSIGNES["fr"]` est la consigne française (révisée par la story de prompt, CAP-6) ; `CONSIGNES["en"]` dit la même chose en anglais et demande des rubriques rédigées en anglais. `CONSIGNE = CONSIGNES["fr"]` reste exporté.
- `<constat>` = `json.dumps({"id", "cvss_vecteur"} + constat.textes(langue).model_dump(), ensure_ascii=False)`, clés dans l'ordre `id, titre, description, impact, recommandation, cvss_vecteur`.
- Libellé de l'actif : `Actif : …` (fr) ou `Asset: …` (en). La note n'est pas traduite.
- La consigne de départ du réglage CAP-6 est celle de l'essai 3 de `bilan-modeles.md`. Son texte final appartient au code, pas au contrat. Le faux moteur exige seulement les balises.

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

**[entériné v2] Signatures.** `composition.ouvrir(config, modele, *, id_lot: str | None = None)` ; `ouvrir_moteur_incident(config, modele, *, id_lot=None)`. `id_lot` nomme le journal `llama-server-<id_lot>.log` (horodatage sinon).

**[v2] Noms publics de `lot.py` (CAP-16, story de socle v2).** Renommages sans changement de comportement :

| v0.1.0 (privé) | v2 (public) |
|---|---|
| `_ID_LOT` | `MOTIF_ID_LOT` (`re.Pattern`, `[0-9A-Za-z][0-9A-Za-z-]{0,63}`, `fullmatch` ; **[revue A3]** 64 caractères au plus) |
| `_Emetteur` | `Emetteur(journal: JournalLot, abonne: Abonne \| None)`, attribut `total`, méthode `emettre(type_, *, index, note, statut, duree_s, details)` |
| `_sans_chemin` | `sans_chemin(message: str) -> str` |
| `_sorties` | `dossier_sorties(config: Configuration) -> Path` (`config.chemins.var / "sorties"`) |

S'y ajoute `verifier_id_lot(id_lot: str, config) -> Path` : la vérification d'un `id_lot` fourni, aujourd'hui dupliquée dans `lot.py` et `incident._id_lot` (motif, `mkdir`, nom réservé Windows → `EntreeInvalide`). Elle renvoie le dossier de sortie ; elle le **crée** et ne sert qu'au lancement d'un lot ou d'un incident. **[revue A3]** S'y ajoute `dossier_lot_existant(id_lot: str, config) -> Path | None`, sans effet de bord (aucun `mkdir`) : `None` si l'id ne vérifie pas `MOTIF_ID_LOT`, est un nom réservé Windows ou ne désigne pas un dossier existant de `dossier_sorties(config)`. Les routes web, `application/lots.py` et `exporter` n'utilisent que `dossier_lot_existant` : un GET ne crée jamais de dossier. `test_architecture.py` interdit, hors de `application/lot.py`, tout import d'un nom de `waveaudit.application.lot` commençant par `_` (tests compris : `tests/e2e/test_lot.py` passe à `lot.sans_chemin`).

**[v2] Lot des fiches.** `executer_lot(requete, config, abonne)` :
1. `langue = requete.langue or config.fiches.langue` ; le workflow reçoit `config.model_copy(update={"fiches": config.fiches.model_copy(update={"langue": langue})})`.
2. Écrit `lot.json` (§30) dès que le dossier de sortie existe, avant l'ouverture du moteur, **s'il n'existe pas déjà** (l'UI l'écrit avant son 303, §26, **[revue A2]**).
3. Après `preparer` et le tri : `relecture.initialiser(dossier_sortie, id_lot=…, langue=…, modele=info.nom_modele, modele_demande=requete.modele, elements=…)` crée `relecture.json` (§25), une entrée `attente` par élément.
4. Après chaque `traiter` et **avant** l'événement de fin de fiche : `relecture.enregistrer_resultat(dossier_sortie, index, resultat)`. Une fiche est donc relisible dès son événement (CAP-10).
5. `lot_demarre.details` reçoit `workflow` et `langue`. L'exporteur de fin de lot est appelé avec `OptionsExport(langue=langue)` (`mode="lot"`) : `rapport.docx` et `fiches.json` sont inchangés.
6. Une exception qui sort d'`executer_lot` laisse `relecture.json` tel quel : les entrées encore `attente` sont les notes non traitées (§25).
7. **[revue A11/E14]** Un échec d'écriture de `relecture.json` (`OSError`, dont `PermissionError` après les réessais du §25) arrête le lot : événement `lot_echoue` (`erreur` = nom de classe, `message` = « Écriture impossible de relecture.json (fichier verrouillé par un autre programme ?) »), puis l'exception remonte (CLI : code 4). Les fiches déjà enregistrées restent relisibles.

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

**[v2] Rôles (CAP-7) et champs facultatifs.**

| nom | role v2 | facultatifs |
|---|---|---|
| `granite-4.0-1b-q4km` | `modele_defaut` | |
| `qwen3.5-0.8b-q4km` | **`modele_repli`** (au lieu de `candidat`) | `reflexion = false` |
| `minicpm5-1b-q4km` | **`candidat`** (au lieu de `modele_repli`) : gardé pour comparer au banc, téléchargé seulement avec `--candidats` | `reflexion = false` |
| `qwen3-1.7b-q4km` | `candidat` | `prefixe_systeme = "/no_think"` |

- Si le rebanc de CAP-7 promeut qwen3-1.7b (au moins 5/6 `ok`, recopie < 0,6, médiane < 40 s sur l'EliteBook), la story de rebanc permute les rôles : `qwen3-1.7b-q4km` devient `modele_defaut` et `granite-4.0-1b-q4km` devient `candidat`. Décision et chiffres consignés dans `bilan-modeles.md`.
- Ordre des entrées dans le fichier : moteur, défaut, repli, puis candidats.
- Champs facultatifs des modèles (`Artefact`, `extra="forbid"`) :
  - `mode_json` (§22) ;
  - `reflexion: bool | None` **[entériné v2]**, §22 ;
  - **[v2]** `repeat_penalty: float | None` (`0 < x <= 2.0`), prime sur `moteur.repeat_penalty` (§3) ;
  - **[v2]** `duree_indicative_s: float | None`, durée médiane par fiche mesurée au banc et affichée par l'UI (§26, `GET /api/modeles`). Valeurs initiales tirées de `bilan-modeles.md`.

**[v2] Modèles installés.** `application/composition.modeles_installes(config) -> list[ModeleInstalle]` (dataclass figée, `application/composition.py`) : `nom, role, taille_o, duree_indicative_s, defaut: bool`.
- En `local-gere` : les artefacts de rôle `modele_defaut`, `modele_repli` ou `candidat` dont `manifeste.chemin(...)` existe sur le disque, dans l'ordre du manifeste. `defaut` vaut vrai pour celui que `choisir_modele(config, artefacts, None)` désigne s'il est installé, sinon pour le premier installé.
- En `externe` : une seule entrée, `nom = moteur.modele_api or "externe"`, `role = "externe"`, `taille_o = 0`, `defaut = True`. **[revue E11]** Quand l'UI reçoit ce nom, elle passe `modele=None` au lot et à la régénération, jamais la chaîne `"externe"`, qui écraserait `modele_api`.
- Seul point d'accès de l'UI au manifeste : `interfaces/web/` n'importe pas `installation` (AD-1).

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
  - sauvegarde puis remplace `socket.socket.connect`, `socket.socket.connect_ex` et `socket.create_connection`, et **[entériné v2]** `socket.socket.sendto` et `socket.socket.sendmsg` (UDP) ;
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

**[v2] Faux moteur** (story de socle v2 ; `SCENARIOS` complété, scénarios v0.1.0 inchangés) :

| Scénario | Comportement |
|---|---|
| `nominal` | inchangé ; en lot `en`, le `<constat>` reçu est en anglais : la sortie est `"[adapté] "` + textes anglais |
| `repetition` | nominal, avec `description` = `("sans restriction d'accès, " * 60)[:longueur]`, où `longueur` = `maxLength` de `description` lu dans `response_format.json_schema.schema` (1 200 par défaut) |
| `langue_anglaise` | nominal, avec `description`, `impact` et `recommandation` remplacées par un texte anglais fixe (`TEXTE_ANGLAIS`, au moins 3 mots-outils anglais par rubrique) ; en mode incident, même chose pour `recit`, `impact` et `recommandation` |
| `langue_francaise` | nominal, avec les mêmes rubriques remplacées par un texte français fixe (`TEXTE_FRANCAIS`) |
| `ecriture_etrangere` | nominal, avec `"経"` ajouté à la fin de `description` (de `recit` en mode incident) |
| `url_de_la_note` | nominal, avec la première URL `https?://\S+` trouvée dans `<note>` (ponctuation finale retirée) ajoutée à `description` ; si aucune, aucune modification |

- Chaque requête reste enregistrée dans `FauxMoteur.requetes` : c'est là qu'on lit `seed` (CAP-1) et `repeat_penalty` (CAP-6).
- Les nouveaux tests de garde-fous unitaires peuvent aussi appeler `appliquer` directement, sans faux moteur.

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
  - un total d'au moins 30 constats ;
  - **[v2]** la présence du bloc `en` (`TextesConstat`), avec ses 4 textes non vides. Erreur : `fichier:id: textes anglais manquants (en.<champ>)`.

**[v2] Schéma YAML bilingue (CAP-8).** Chaque entrée garde ses champs v0.1.0 (textes français à la racine) et reçoit un bloc `en` :

```yaml
- id: WEB-XSS-REFLECHI
  titre: Injection de script réfléchie (XSS réfléchi)
  famille: web
  mots_cles: [...]            # inchangés, déjà fr + en
  description: >- ...
  impact: >- ...
  recommandation: >- ...
  en:
    titre: Reflected cross-site scripting (XSS)
    description: >- ...
    impact: >- ...
    recommandation: >- ...
  cvss_vecteur: ...           # inchangé
  references: [...]           # inchangées : id, titre et url non traduits
  source: ...
```

- `CatalogueYaml` refuse au chargement une entrée sans `en` complet (`ConfigurationInvalide`, `fichier:index: textes anglais manquants`). La story qui introduit le schéma traduit donc les 50 entrées du catalogue en une fois.
- Anaël relit un échantillon de 10 constats avant fusion (CAP-8).
- `test_catalogue.py` vérifie aussi que, pour chaque entrée, `en.titre != titre` et que `en.description` ne contient aucun mot-outil français au sens du §6 étape 6 (garde-fou de langue appliqué au catalogue).
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
- **[entériné v2]** Un thème privé invalide (`theme.toml` illisible, `modele.docx` illisible) lève `ConfigurationInvalide` (code 2) dès le constructeur `ExportDocx(theme_prive)`, donc avant le démarrage du moteur.
- **[v2]** Libellés par langue (`OptionsExport.langue`) et modes `final` / `brouillon` : §27. Les libellés français ci-dessus restent ceux de `langue="fr"`. `BANDEAU` reste la constante publique française ; `BANDEAUX: dict[Langue, str]` est ajouté.

## 18. Interface web — `interfaces/web/`

**[v2]** L'API HTTP complète de la v2 est au §26, qui prime sur cette section. Les règles ci-dessous restent valables, avec les écarts entérinés :
- **[entériné v2]** `Host: [::1]:<port>` est accepté (origine `http://[::1]:<port>` aussi) ;
- **[entériné v2]** `GET /lots/{id}/etat?depuis=N` (facultatif, `N >= 0`) ne renvoie que les événements d'indice `>= N` ; `0` donne la réponse complète.

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
- **[entériné v2]** `--modele` inconnu est vérifié contre le manifeste avant tout traitement (code 2), y compris pour `incident`, où le moteur n'est pas ouvert sans détection. Les messages d'erreur passent par `lot.sans_chemin` : aucun chemin absolu.
- **[v2] Ajouts** (les commandes, options et codes v0.1.0 ne changent pas) :
  - `fiches DOSSIER [...] [--langue fr|en]` : défaut `config.fiches.langue`. Une valeur hors liste est refusée par typer (code 2). Le bandeau console reste français.
  - `banc DOSSIER [--modele NOM] [--langue fr|en]` (§29).
  - `exporter LOT [--brouillon] [--config F]` (§27).
  - `incident` ne reçoit pas `--langue` : le rapport d'incident reste en français.

## 20. Banc — `application/banc.py`

- **Fonctionnement :** le banc est un abonné du lot. Il lit `pid_moteur` dans `lot_demarre`, puis échantillonne toutes les 0,5 s, dans son propre thread, `MesureMemoire.rss_octets` de l'application (`os.getpid()`) et du moteur, jusqu'à `lot_termine` ou `lot_echoue`.
- **`var/sorties/<id>/banc.json` :** `{"id_lot", "modele", "fiches": [{"note", "duree_s"}], "duree_mediane_s", "duree_max_s", "pic_rss_app_o", "pic_rss_moteur_o", "pic_rss_total_o", "top1", "top3", "etiquetees"}`. `top1` et `top3` sont calculés depuis `tracabilite` et `EntreeEcartee`.
- **Affichage :** un résumé lisible en console.
- **[entériné v2]** `pic_rss_total_o` = maximum, sur les échantillons, de la somme application + moteur **au même instant** (et non la somme des deux pics).
- **[v2]** Champs ajoutés et indicateur de recopie : §29.

## 21. Workflow incident (CERT) — `domaine/incident.py`, `workflows/incident/`, `application/incident.py`

Ajouté le 2026-10-17 (SPEC-waveaudit-cert), révisé après la revue adversariale (`specs/spec-waveaudit-cert/reviews/review-adversariale.md`). C1 crée les formes, ports, constantes, fixtures et les deux extractions du socle (journal, moteur) ; C2 à C6b les appliquent sans toucher au socle. Conditions des règles, champs, chronologie de démo et oracle : `formats-incident.md` (normatif).

**[v2] Écarts entérinés et ajouts au workflow incident :**
- **[entériné v2]** Signatures : `ExporteurIncidentDocx(theme_prive, *, max_preuves: int)` ; `assembler_rapport(lecture, recits, regles: dict[str, Regle])` (les `recommandations` type sont lues dans `regles`).
- **[entériné v2]** Neutralisation du point final avant les motifs (garde-fous, étapes 2 et 3) : on cherche les jetons sur une copie de même longueur, où chaque suite de `.` suivie d'un blanc, d'une ponctuation fermante ou séparatrice (`) ] } > » " ' ” ’ , ; : ! ?`) ou de la fin du texte devient autant d'espaces. Un `.` suivi d'un chiffre n'est jamais touché. Les positions trouvées servent à retirer les jetons du texte d'origine.
- **[v2] CAP-1** : la nouvelle tentative du récit passe `seed=config.moteur.seed + 1` (§5).
- **[v2] CAP-4** : `appliquer_recit(..., motifs_initiaux=(), langue: Langue = "fr")`. Après l'étape 5 (complétion), les étapes 5 et 6 du §6 v2 (répétition, puis langue) s'appliquent aux rubriques non complétées : l'écriture sur `titre`, `recit`, `impact` et `recommandation` ; les mots-outils sur `recit`, `impact` et `recommandation`. Le service passe toujours `langue="fr"` : le rapport d'incident reste en français en v2. **[revue A19/E36]** Le texte source passé à `est_repetitif` et `motif_langue` est la concaténation des lignes de preuve de la détection.
- **[v2]** Prompt : échappement des balises `regle` et `preuves` dans chaque ligne de preuve, même forme qu'au §8.
- **[v2]** Le service incident écrit `lot.json` (§30, `workflow="incident"`, `langue=None`) et utilise `lot.Emetteur`, `lot.verifier_id_lot`, `lot.sans_chemin` et `lot.dossier_sorties` (noms publics, §9).

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

**[entériné v2] État livré par V1.** `moteur.mode_json` et le champ `mode_json` du manifeste existent (aucune entrée ne le renseigne). S'y ajoute un champ facultatif `reflexion: bool | None` par entrée du manifeste :
- `None` (absent) : rien n'est envoyé ;
- un booléen : transmis en `chat_template_kwargs = {"enable_thinking": <valeur>}`.

`minicpm5-1b-q4km` et `qwen3.5-0.8b-q4km` portent `reflexion = false` : sans lui, leur `content` arrive vide.

## 23. Langue d'un lot de fiches (CAP-8) — `domaine/modeles.py`, `workflows/fiches/`, `adaptateurs/export_docx.py`

Ajouté le 2026-10-18 (v2).

- **Valeurs :** `Langue = Literal["fr", "en"]`. Défaut : `config.fiches.langue` (`"fr"`), donc un lot sans choix se comporte comme en v0.1.0.
- **Choix :** fixé au lancement, jamais modifié ensuite. Sources : `RequeteLot.langue`, option CLI `--langue` (§19), champ `langue` de `POST /lots` (§26). La langue est consignée dans `lot.json` (§30), `relecture.json` (§25) et `lot_demarre.details`.
- **Effets, et rien d'autre :**
  - consigne `CONSIGNES[langue]` et textes du constat `constat.textes(langue)` dans le prompt (§8) ;
  - repli et complétion des garde-fous (§6) depuis `constat.textes(langue)` ;
  - langue vérifiée par le garde-fou (§6 étape 6) ;
  - libellés et bandeau du Word (§27) ;
  - la recopie du banc compare au texte du constat dans la langue du lot (§29).
- **Ce qui ne change pas :** l'index BM25, toujours bilingue (§7) ; les notes, jamais traduites ; les références (`id`, `titre`, `url`) ; l'UI, en français, avec l'attribut `lang` de la langue du lot sur le panneau note et le formulaire de fiche ; la sortie console de la CLI ; le workflow incident, en français.

## 24. Verrou unique et moteur à la demande — `application/moteur_demande.py`

Ajouté le 2026-10-18 (v2, CAP-9, CAP-11, CAP-14).

```python
@dataclass(frozen=True)
class Occupation:
    nature: Literal["fiches", "incident", "regeneration"]; id_lot: str; index: int | None; debut: datetime
class VerrouUnique:                       # un par processus UI, créé par creer_app
    def prendre(self, occupation: Occupation) -> bool: ...   # non bloquant ; False si déjà pris
    def definir(self, occupation: Occupation) -> None: ...   # [revue A1] remplace l'occupation provisoire, verrou déjà pris
    def liberer(self) -> None: ...
    def occupation(self) -> Occupation | None: ...           # copie, sous verrou interne
class MoteurALaDemande:                   # un par processus UI, créé par creer_app
    def __init__(self, config: Configuration) -> None: ...   # inactivite_s = config.ui.inactivite_moteur_s
    @contextmanager
    def utiliser(self, modele: str | None) -> Iterator[tuple[Ports, InfoMoteur]]: ...
    def fermer(self) -> None: ...         # idempotent
```

- **Un seul travail à la fois :** lot de fiches, lot incident et régénération prennent le même `VerrouUnique`. Prise en échec : HTTP 409 `lot_en_cours`, rien n'est écrit. Le verrou est rendu dans un `finally` du fil de travail, ou avant son démarrage si la requête échoue.
- **Un seul llama-server à la fois :** un lot ou un incident, une fois le verrou pris, appelle `MoteurALaDemande.fermer()` avant `executer_lot` / `executer_incident`. Ces deux services gardent leur cycle de vie (AD-11) : ouverture au début, fermeture à la fin. La CLI n'utilise ni l'un ni l'autre.
- **[revue A10/E1] Concurrence interne :** `VerrouUnique` et `MoteurALaDemande` protègent leur état par un `threading.Lock` interne. `MoteurALaDemande` tient un compteur d'usages en cours ; l'entrée dans `utiliser` incrémente le compteur et annule la minuterie sous ce verrou ; l'échéance de la minuterie ne ferme le moteur que si, sous ce verrou, le compteur vaut 0 et que la minuterie échue est encore la minuterie courante. `fermer()` prend le même verrou. Test de concurrence (M1) : minuterie à 0,01 s et `utiliser` en boucle dans deux fils, aucun moteur fermé pendant un usage.
- **`utiliser(modele)`**, appelé seulement sous le verrou (régénération) :
  - **[revue E10]** la clé de réutilisation est le nom résolu : `choisir_modele(config, artefacts, modele).nom` en local-gere (qui fige le choix défaut/repli au premier usage), `modele or moteur.modele_api` en externe ; jamais la chaîne demandée telle quelle ;
  - le moteur est-il déjà ouvert pour ce nom ? On le réutilise ;
  - sinon, on ferme l'ancien, puis `composition.ouvrir(config, modele)` (journal `llama-server-<horodatage>.log`) et `ports.moteur.sonder()`. Un échec referme et remonte `MoteurInjoignable` ou `ConfigurationInvalide`.
- **Arrêt après inactivité :** en sortie de bloc, un `threading.Timer(inactivite_s)` est armé (le précédent est annulé). À l'échéance, le moteur est fermé si aucun `utiliser` n'est en cours. `fermer()` est aussi appelé à l'arrêt de l'application (lifespan FastAPI). **[revue E3]** À l'arrêt, le lifespan attend la fin de l'usage en cours au plus 10 s, puis ferme ; une entrée restée `generation="en_cours"` est lue ensuite comme interrompue (§25).
- **Mode `externe` :** même objet, sans processus ; `utiliser` ouvre et réutilise le client `MoteurOpenAI`.
- **Modèle [revue A15/A16] :** la régénération utilise le modèle **résolu** du lot, pas la demande brute : en local-gere `etat.modele` (nom de l'entrée du manifeste retenue au démarrage du lot, donc indépendant de la RAM du moment) ; en externe `etat.modele_demande` (souvent `None`, donc `modele_api`). Le nom utilisé est consigné dans `EntreeRelecture.modele_generation`. Si ce modèle n'est plus installé (absent de `modeles_installes`), la route refuse avant tout démarrage : 422 `modele_indisponible` (message de Voice and Tone), rien n'est écrit ; `generable` vaut alors `false`.

## 25. État de relecture d'un lot — `domaine/relecture.py`, `application/relecture.py`

Ajouté le 2026-10-18 (v2, CAP-10 à CAP-13, CAP-17). Fichier `var/sorties/<id_lot>/relecture.json`, UTF-8, `EtatRelecture.model_dump_json(indent=2)`.

### Formes (`domaine/relecture.py`, story de socle v2)

Toutes `ConfigDict(extra="forbid", frozen=True)`.

```python
StatutRelecture = Literal["a_valider", "validee"]
EtatEntree = Literal["attente", "fiche", "ecartee"]
EtatGeneration = Literal["aucune", "en_cours", "echec"]
class FicheCorrigee(BaseModel):
    titre: str; description: str; impact: str; recommandation: str
    cvss_vecteur: str                 # saisi tel quel (≤ 100 caractères), éventuellement invalide
    cvss: Cvss | None                 # cvss31.evaluer(cvss_vecteur), None si invalide
    references: list[Reference]       # sous-ensemble ordonné de fiche_generee.references
class EntreeRelecture(BaseModel):
    index: int                        # >= 1, rang dans le lot (tri casefold) = index des événements
    note: str                         # nom de fichier seul
    source: Note | None               # None pour une NoteInvalide
    raison_invalide: str | None
    etat: EtatEntree
    candidats: list[Candidat]         # top 3 de la recherche (vide pour une note invalide)
    candidat_choisi: str | None       # constat de la fiche courante
    fiche_generee: Fiche | None
    fiche_corrigee: FicheCorrigee | None
    ecartee: EntreeEcartee | None
    statut_relecture: StatutRelecture | None
    generation: EtatGeneration = "aucune"
    erreur_generation: str | None = None
    modele_generation: str | None = None  # [revue A16] nom du modèle qui a produit fiche_generee (InfoMoteur.nom_modele)
    version: int = 1                  # +1 à chaque écriture de cette entrée
class EtatRelecture(BaseModel):
    version_schema: Literal[1] = 1
    id_lot: str; langue: Langue
    modele: str                       # nom affiché (InfoMoteur.nom_modele)
    modele_demande: str | None        # RequeteLot.modele tel que reçu ; repassé tel quel à la régénération
    entrees: list[EntreeRelecture]    # triées par index
class RefusRelecture(EntreeInvalide):  # code machine repris tel quel par l'API (§26)
    def __init__(self, code: str, message: str) -> None: ...
```

Invariants (validateurs) :
- `etat == "fiche"` ⇔ `fiche_generee` et `statut_relecture` renseignés ;
- `etat == "ecartee"` ⇔ `ecartee` renseignée ;
- `fiche_corrigee` ⇒ `etat == "fiche"` ;
- `candidat_choisi` ∈ `{c.id for c in candidats}` ou `None`, **[revue A14]** sauf pour une entrée générée depuis `non_rattachee` : `candidat_choisi` est alors un id du catalogue, hors `candidats` (contrôle d'existence par la route, pas par le validateur).

### Règles pures (`domaine/relecture.py`)

- `fiche_courante(e) -> Fiche` : `fiche_generee` sans correction. Avec une correction, `fiche_generee.model_copy` avec les 4 textes, `references` et `cvss` corrigés ; si `cvss` corrigé vaut `None`, le `cvss` généré est gardé (brouillon seulement : une fiche validée a toujours un CVSS valide). `statut`, `motifs` et `tracabilite` restent ceux de la génération (« signalé à la génération »).
- `corriger(e, correction, longueur_max) -> EntreeRelecture`. Refus :
  - `non_modifiable` si `etat != "fiche"` ;
  - `generation_en_cours` ;
  - `rubrique_trop_longue` (au-delà de `longueur_max`) ;
  - `reference_ajoutee` (id absent de `fiche_generee.references`) ;
  - **[revue E29]** `reference_dupliquee` (même id deux fois).

  Sinon, `cvss` recalculé et `statut_relecture = "a_valider"`. Les références gardées sont rangées dans l'ordre de `fiche_generee.references`, quel que soit l'ordre reçu. Une correction identique à l'état courant ne change rien (pas d'incrément de version). **[revue E30]** Un vecteur invalide est enregistré tel quel (`cvss = None`) : la saisie n'est pas perdue, la validation est refusée et le brouillon montre le CVSS généré (règle de `fiche_courante`).
- `valider(e) -> EntreeRelecture`. Refus :
  - `non_modifiable` ;
  - `generation_en_cours` ;
  - `vecteur_invalide` (CVSS corrigé `None`) ;
  - `rubrique_vide` (un texte vide après strip).

  Sinon `statut_relecture = "validee"`.
- `remplacer_fiche(e, fiche: Fiche, constat_id, modele_generation: str) -> EntreeRelecture` : `etat="fiche"`, `fiche_generee=fiche`, `fiche_corrigee=None`, `candidat_choisi=constat_id`, `ecartee=None`, `statut_relecture="a_valider"`, `generation="aucune"`, `erreur_generation=None`, `modele_generation` **[revue A16]**.
- `rapport_export(etat, mode: Literal["final","brouillon"]) -> tuple[Rapport, frozenset[str]]` :
  - **final** : `fiches` = `fiche_courante` des entrées `validee` ;
  - **brouillon** : `fiches` = toutes les entrées `fiche`, et l'ensemble renvoyé = notes des entrées `a_valider` ;
  - **[revue A17] final** : l'ensemble renvoyé = notes des entrées `fiche` encore `a_valider` ; l'exporteur les liste dans l'annexe (§27), jamais dans le corps ;
  - **les deux** : `ecartees` = entrées `ecartee`, plus les entrées `attente` converties en `EntreeEcartee(non_traitee, Motif(lot_interrompu, "lot interrompu avant cette note"), candidats=[], constat_attendu=source.constat_attendu if source else None)` **[revue E17]**. Ordre : `index`.

### Persistance (`application/relecture.py`)

- `FICHIER = "relecture.json"`. Le module n'importe ni `lot.py` ni `moteur_demande.py` au niveau module (`lot.py` l'importe : pas de cycle) ; `sans_chemin` est importé dans `regenerer`, `MoteurALaDemande` sous `TYPE_CHECKING`.
- Écritures, toutes sous un verrou propre au fichier : `_VERROUS: dict[str, threading.Lock]` indexé par le chemin résolu, créé sous un verrou global. Chaque écriture fait lire, modifier, puis écrire de façon atomique :
  - écriture dans `.relecture.json.partiel` ;
  - puis `os.replace`, retenté **10 fois à 100 ms** d'écart sur `PermissionError` (lecteur Windows concurrent, antivirus, indexeur) **[revue A11/E14]**. Après le dernier essai, le `.partiel` est supprimé et la `PermissionError` remonte : le lot échoue (§9, étape 7) ; l'API répond 503 `ecriture_impossible` (§26). Test (R2) avec `relecture.json` tenu ouvert par un autre descripteur (Windows) et avec `os.replace` simulé en échec (toutes plates-formes).
- Seul écrivain de `relecture.json`. Lecture sans verrou possible : le remplacement est atomique.
- `initialiser(dossier, *, id_lot, langue, modele, modele_demande, elements)` : une entrée `attente` par élément, `index` 1..n. Une `Note` donne `source = note` ; une `NoteInvalide` donne `source=None` et `raison_invalide`.
- `enregistrer_resultat(dossier, index, resultat: ResultatElement)` :
  - `Fiche` → `etat="fiche"`, `candidats = tracabilite.candidats`, `candidat_choisi = constat_id`, `statut_relecture="a_valider"` ;
  - `EntreeEcartee` → `etat="ecartee"`, avec ses `candidats`.
  - `version + 1`, sans contrôle de version.
- `charger(dossier) -> EtatRelecture`. Sans `relecture.json` mais avec `fiches.json` (lot v0.1.0) : état reconstruit en mémoire, sans l'écrire :
  - toutes les fiches `a_valider`, les entrées écartées en `ecartee`, `source=None` ;
  - `langue="fr"`, `modele` lu dans `lot_demarre` (sinon `""`), `modele_demande = None` ;
  - la première modification l'écrit.

  **[revue E9]** Les entrées reconstruites (fiches et écartées réunies) sont triées par nom de note `casefold`, puis numérotées `index` 1..n : le rang est stable d'une lecture à l'autre. **[revue E8/A15]** Elles ont `source=None` : elles sont relisibles, corrigeables, validables et exportables, mais jamais régénérables (`generable=false`, refus `source_absente`).

  **[revue A12/E16]** Avec `lot.json` (`workflow="fiches"`) mais sans `relecture.json` ni `fiches.json` (lot pas encore initialisé, ou échoué avant `initialiser`) : `EtatRelecture` vide (`entrees=[]`, `langue` et `modele_demande` lus dans `lot.json`, `modele=""`), sans écriture.

  Sans aucun des trois : `RefusRelecture("lot_inconnu")`.
- `modifier(dossier, index, version_attendue, operation, *, occupation=None) -> EntreeRelecture` : `version_attendue != version` → `RefusRelecture("conflit_version")`. Sinon `operation(entree)` (une règle pure ci-dessus) et `version + 1`. La lecture sous verrou applique la normalisation « génération interrompue » ci-dessous.
- `regenerer(config, dossier, index, constat_id, moteur: MoteurALaDemande) -> None` : exécuté dans le fil de travail, sous le `VerrouUnique` déjà pris (§24).
  1. `with moteur.utiliser(<modèle résolu du lot, §24>) as (ports, info)` **[revue A16]** ;
  2. `pipeline.creer(config_lot, ports).rediger(source, constat_id, candidats)`, où `config_lot` porte la langue du lot ;
  3. `modifier(..., remplacer_fiche(..., modele_generation=info.nom_modele))` sans contrôle de version.

  Le repli des garde-fous donne toujours une fiche, **sauf** :
  - **[revue E2]** une fiche dont les motifs contiennent `repli_moteur` (moteur injoignable pendant la génération) ne remplace pas la fiche courante : `generation="echec"`, `erreur_generation="Le moteur de génération ne répond pas ; la fiche n'a pas été régénérée."` ;
  - l'échec d'ouverture du moteur : `generation="echec"` et `erreur_generation` (message passé par `sans_chemin`) ;
  - **[revue E4]** toute autre exception de `regenerer` : `generation="echec"`, `erreur_generation = sans_chemin(str(exc))` (journalisée), et le verrou est libéré dans le `finally` du fil. Une régénération n'émet aucun `EvenementLot` et n'écrit pas dans `journal.jsonl` : sa trace est dans `relecture.json` (`candidat_choisi`, `version`).
- `demarrer_regeneration(dossier, index, version_attendue, constat_id, confirmer) -> EntreeRelecture` : vérifie, puis passe `generation="en_cours"` (version + 1) avant le lancement du fil. Refus, dans cet ordre :
  - `conflit_version` ;
  - `generation_en_cours` ;
  - `non_generable` : entrée `attente`, ou `ecartee` `non_traitee` ;
  - **[revue A15/E8]** `source_absente` : `source` vaut `None` (lot v0.1.0 reconstruit) ;
  - **[revue E7]** `candidat_courant` : `constat_id == candidat_choisi` ;
  - `candidat_inconnu` : **[revue A14]** pour une entrée `fiche`, `constat_id` hors `candidats` ; pour une entrée `ecartee` `non_rattachee`, `constat_id` absent du catalogue (choix dans tout le catalogue, les 3 candidats à score nul n'ont pas de sens) ;
  - `confirmation_requise` : `fiche_corrigee` renseignée **ou** `statut_relecture == "validee"` **[revue E6]**, et `confirmer` faux.
- **Génération interrompue [revue A4/E5/E26] :** une entrée lue avec `generation="en_cours"` alors que l'occupation courante n'est pas `(regeneration, id_lot, index)` est **présentée** `generation="echec"`, `erreur_generation="génération interrompue"`. Ce calcul se fait à la lecture, en mémoire, sans écriture ni incrément de version : `charger(dossier, *, occupation=None)` et la lecture sous verrou de `modifier` / `demarrer_regeneration` l'appliquent. Aucun GET n'écrit ; une régénération fraîche ne peut pas être écrasée par une lecture concurrente.
- **Relance :** relancer des notes crée toujours un nouveau lot ; aucun code ne réécrit le `relecture.json` d'un autre lot.

## 26. API HTTP v2 de l'interface web — `interfaces/web/app.py`

Ajouté le 2026-10-18 (v2, CAP-9 à CAP-15). Prime sur le §18 (le reste du §18 reste valable).

### Règles communes

- **Création :** `creer_app(config, *, hotes_test: tuple[str, ...] = ()) -> FastAPI` crée `VerrouUnique`, `MoteurALaDemande` et `app.state.jeton_csrf = secrets.token_urlsafe(32)`. **[revue A7/E27]** `hotes_test` n'est renseigné que par `tests/web_outils.py` (`("testserver",)`) ; la commande `ui` appelle `creer_app(config)`, sans `testserver`. Le garde réseau n'est pas activé ici (inchangé). Lifespan : `MoteurALaDemande.fermer()` à l'arrêt.
- **Middleware, dans cet ordre :**
  1. `Host`, comparé après `lower()` **[revue E28]**, hors `{127.0.0.1:<port>, localhost:<port>, [::1]:<port>}` ∪ `hotes_test` (et, si `<port>` vaut 80, les mêmes hôtes sans port) → 400 `hote_refuse` ;
  2. sur `POST`/`PUT` : `Origin` présent et hors `http://<hôte autorisé>` → 403 `origine_refusee` ;
  3. sur `POST`/`PUT` : en-tête `X-CSRF-Token` absent ou différent de `app.state.jeton_csrf` (`secrets.compare_digest`) → 403 `csrf_invalide` ;
  4. sur `POST`/`PUT` : `Content-Length` absent → 411 `longueur_requise` ; supérieur à la limite de la route → 413 `trop_volumineux` (`"limite": "total"`). Limites totales : `POST /lots` 20 Mio ; `POST /incidents` 50 Mio ; les autres 256 Kio.
- **[revue A5/E42] Trois limites de dépôt, une règle :** la limite totale (en-tête `Content-Length`, enveloppe multipart comprise) est la seule garantie de mémoire ; les limites par fichier et par nombre la précisent sans la contredire. Fiches : au plus 100 fichiers, 1 Mio chacun, 20 Mio au total. Incident : au plus 50 fichiers, 10 Mio chacun, 50 Mio au total. Un dépôt peut donc respecter les limites par fichier et dépasser le total : le message le dit. Codes : 413 `trop_volumineux` avec `"limite": "fichier"` (message de Voice and Tone : nom et taille du fichier) ou `"limite": "total"` (« Le dépôt dépasse 20 Mo au total (23,4 Mo). Déposez les notes en plusieurs lots. ») ; 400 `trop_de_fichiers` (« Le dépôt compte 120 fichiers ; 100 au plus par lot. »).
- **En-têtes de toute réponse :**
  - `Content-Security-Policy: default-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'` ;
  - `X-Content-Type-Options: nosniff` ;
  - `Referrer-Policy: no-referrer` ;
  - `Cache-Control: no-store` sur les réponses JSON **et HTML** **[revue E25]** (une page en cache garderait un jeton CSRF périmé).
- **[revue E25] Jeton après redémarrage :** `GET /api/jeton` → 200 `{"jeton"}`. Sur un 403 `csrf_invalide`, le JS relit le jeton une fois et rejoue la requête ; un second 403 affiche « Le serveur a redémarré. Rechargez la page ; vos corrections enregistrées sont conservées. ».
- **Pages :**
  - chaque gabarit porte `<meta name="csrf" content="{{ jeton_csrf }}">` ; le JS le renvoie dans `X-CSRF-Token` à chaque `POST`/`PUT` (formulaires multipart compris, envoyés par `fetch`) ;
  - aucun `<script>` en ligne, aucun attribut `style=`, aucun attribut `on*=` : la CSP les bloque ;
  - le bandeau est en haut et en bas de chaque page (AD-14) ;
  - `<html lang="fr">`.
- **Erreurs JSON :** `{"detail": "<message français, sans chemin absolu>", "code": "<code>"}`, plus des champs propres à certains codes (`occupation`, `entree`). Les messages de `EXPERIENCE.md` (Voice and Tone) sont repris tels quels pour `trop_volumineux`, `nom_refuse`, `lot_en_cours`, `moteur_injoignable` et `modele_indisponible`.
- **Identifiant de lot dans un chemin :** `lot.dossier_lot_existant` (§9) **[revue A3]**, sans effet de bord ; `None` → 404 `lot_inconnu`. Aucun GET ne crée de dossier. Une page `/lots/{id}` d'un lot incident redirige (303) vers `/incidents/{id}`, et inversement.
- **`index` :** entier `>= 1` et `<=` nombre d'entrées, sinon 404 `entree_inconnue` **[revue E21]**.
- **[revue A6/E41] Noms de fichiers déposés (notes et journaux) :** en plus des règles du §18, un nom terminé par `.` ou par une espace est refusé (`nom_refuse`) ; les doublons sont comparés après `rstrip(". ").casefold()`. Windows ne peut donc jamais écraser un fichier par un autre du même dépôt.
- **[revue A13/E12] Lot en cours dans un autre processus :** un lot dont `application/lots.etat_lot` donne `en_cours` sans que l'occupation de ce processus le porte (lot CLI, ou autre instance UI) est en lecture seule : `PUT …/correction`, `POST …/validation`, `POST …/candidat` et `POST …/export` répondent 409 `lot_en_cours_externe` (« Ce lot est en cours dans un autre programme (CLI). Attendez sa fin pour le modifier ou l'exporter. »). Le double llama-server reste possible (accepté, Constraints de la SPEC).
- **[revue A11/E15] Écriture impossible :** une `PermissionError` qui survit aux réessais du §25 donne 503 `ecriture_impossible` (« Enregistrement impossible : le fichier du lot est verrouillé par un autre programme. Réessayez dans un instant. »), sans changer l'état.

### Routes

| Méthode et chemin | Entrée | Succès | Erreurs |
|---|---|---|---|
| `GET /` | — | HTML accueil : workflows, modèles (`modeles_installes`, défaut présélectionné), langues (fiches), occupation courante, lien « Lots récents » s'il existe au moins un lot | — |
| `GET /lots` | — | HTML lots récents | — |
| `GET /api/lots` | — | 200 `{"lots": [ResumeLot]}` (§30), au plus 50, `id_lot` décroissant | — |
| `GET /api/modeles` | — | 200 `{"modeles": [{"nom","role","taille_o","duree_indicative_s","defaut"}], "langues": ["fr","en"], "langue_defaut"}` | — |
| `POST /lots` | multipart : `notes` (1 à 100 fichiers, règles de nom du §18, au plus 1 Mio chacun), `modele` (facultatif, nom de `/api/modeles`), `langue` (facultatif, `fr`\|`en`) | 303 → `/lots/{id}` | 409 `lot_en_cours` (+`occupation`, rien d'écrit) ; 400 `nom_refuse` ; 400 `aucune_note` ; 413 `trop_volumineux` ; 422 `modele_indisponible` ; 422 `langue_invalide` |
| `GET /lots/{id}` | — | HTML suivi et relecture | 404 |
| `GET /lots/{id}/etat?depuis=N` | `N >= 0` | 200 `{"id_lot","workflow","etat","total","evenements","erreur"}` (§30) | 404 |
| `GET /api/jeton` | — | 200 `{"jeton"}` **[revue E25]** | — |
| `GET /lots/{id}/relecture` | — | 200 `{"id_lot","langue","modele","etat_lot","non_validees": int,"entrees": [{"index","note","etat","statut_generation","statut_relecture","generation","version","titre"}]}` ; `entrees` vide si le lot n'est pas encore initialisé **[revue A12]** ; `non_validees` = nombre de fiches `a_valider` (confirmation d'export, **[revue A17]**) | 404 |
| `GET /lots/{id}/entrees/{index}` | — | 200 `{"entree": EntreeRelecture, "fiche_courante": Fiche\|null, "candidats_detail": [{"id","score","titre"}], "generable": bool, "modifiable": bool}` ; les titres sont dans la langue du lot ; génération interrompue calculée à la lecture, sans écriture **[revue A4]** | 404 |
| `GET /lots/{id}/catalogue` | — | 200 `{"constats": [{"id","famille","titre"}]}`, tout le catalogue trié par `id`, titres dans la langue du lot ; sert au choix d'une entrée `non_rattachee` (liste filtrable côté client) **[revue A14]** | 404 |
| `PUT /lots/{id}/entrees/{index}/correction` | JSON `{"version","titre","description","impact","recommandation","cvss_vecteur","references": [id]}` | 200 `{"entree"}` | 409 `conflit_version` (+`entree`), `generation_en_cours`, `lot_en_cours_externe` ; 422 `non_modifiable`, `rubrique_trop_longue`, `reference_ajoutee`, `reference_dupliquee`, `corps_invalide` ; 503 `ecriture_impossible` |
| `POST /lots/{id}/entrees/{index}/validation` | JSON `{"version"}` | 200 `{"entree"}` | 409 `conflit_version`, `generation_en_cours`, `lot_en_cours_externe` ; 422 `non_modifiable`, `vecteur_invalide`, `rubrique_vide` ; 503 `ecriture_impossible` |
| `POST /lots/{id}/entrees/{index}/candidat` | JSON `{"version","constat_id","confirmer": false}` | 202 `{"entree"}` (`generation="en_cours"`), suivi en relisant l'entrée | 409 `lot_en_cours` (verrou), `lot_en_cours_externe`, `conflit_version`, `generation_en_cours`, `confirmation_requise` ; 422 `non_generable`, `source_absente`, `candidat_courant`, `candidat_inconnu`, `modele_indisponible` ; 503 `ecriture_impossible` |
| `POST /lots/{id}/export` **[revue A4/E26]** | JSON `{"type": "final"\|"brouillon"}`, jeton CSRF | 200 docx en pièce jointe, nommé `rapport-<id>.docx` ou `brouillon-<id>.docx` (§27) ; en final, en-tête `X-Non-Validees: <n>` | 404 ; 409 `lot_en_cours` (ce lot tourne), `lot_en_cours_externe`, `aucune_fiche_validee` (final), `export_verrouille` (`PermissionError`) ; 422 `type_invalide` |
| `GET /lots/{id}/rapport.docx` | — | v0.1.0 inchangé (rapport de fin de lot) | 404 ; 409 `lot_non_termine` |
| `POST /incidents` | multipart : `journaux` (1 à 50 fichiers, au plus 10 Mio chacun ; nom `^[A-Za-z0-9][A-Za-z0-9 ._-]{0,99}$`, noms réservés Windows et doublons refusés), `modele` (facultatif), `annee` (facultatif, 1970 à 2100, année courante par défaut) | 303 → `/incidents/{id}` | 409 `lot_en_cours` ; 400 `nom_refuse`, `aucun_journal_reconnu` (aucun fichier routé selon `composition.journal_reconnu`) ; 413 ; 422 `modele_indisponible`, `annee_invalide` |
| `GET /incidents/{id}` | — | HTML suivi et résultat | 404 |
| `GET /incidents/{id}/etat?depuis=N` | — | forme de `/lots/{id}/etat` | 404 |
| `GET /incidents/{id}/resultat` | — | 200 `{"id_lot","rapport": RapportIncident, "par_severite": {"critique","elevee","moyenne","faible"}, "total"}` | 404 ; 409 `lot_non_termine` |
| `GET /incidents/{id}/rapport-incident.docx` | — | docx | 404 ; 409 `lot_non_termine` |
| `GET /theme/logo.svg` | — | `image/svg+xml`, `theme-prive/web/logo.svg` (§28) | 404 `logo_absent` |
| `GET /static/{fichier}` | — | fichiers statiques locaux | 404 |

- **Lancement d'un lot ou d'un incident**, dans cet ordre **[revue A1/A2]** :
  1. `VerrouUnique.prendre(Occupation(nature, id_lot="", index=None, debut))` (occupation provisoire) ;
  2. validation des fichiers, du modèle et de la langue ;
  3. `nouvel_id_lot` ;
  4. `VerrouUnique.definir(Occupation(nature, id_lot=id, index=None, debut))` ;
  5. écriture dans `var/entrees/<id>/` ;
  6. écriture synchrone de `var/sorties/<id>/lot.json` (§30, `lot.ecrire_fiche_lot`), avant le 303 : la page suivante connaît déjà le workflow ;
  7. `MoteurALaDemande.fermer()` ;
  8. fil `daemon` qui exécute `executer_lot(RequeteLot(dossier, id_lot=id, modele, langue))` ou `executer_incident(RequeteIncident(dossier, annee, modele, id_lot=id))`, puis libère le verrou dans un `finally`.

  Tout refus libère le verrou ; un refus après l'étape 3 supprime aussi `var/entrees/<id>/` et `var/sorties/<id>/`. En `externe`, `modele` vaut le seul nom proposé par `/api/modeles`, passé au lot comme `None` (§11).
- **Changement de candidat :** `VerrouUnique.prendre(Occupation("regeneration", id, index))`, puis `relecture.demarrer_regeneration`, puis le fil `relecture.regenerer`, qui libère le verrou à la fin. Un refus de `demarrer_regeneration` libère aussitôt le verrou.
  - **[revue A9/E24] Côté client :** avant le POST, le JS vide sa file d'enregistrement (attend le PUT en vol, envoie le corps en attente) et utilise la `version` ainsi obtenue. Il demande confirmation si l'entrée relue porte une correction ou est validée (règle serveur) ; le serveur reste juge (`confirmation_requise`).
  - **[revue A14]** Pour une entrée `ecartee` `non_rattachee`, le choix se fait dans la liste filtrable de `GET /lots/{id}/catalogue` ; pour une fiche, dans ses 3 candidats.
- **Enregistrement des corrections [revue A8/E23] :** le client envoie le corps complet de la fiche à chaque anti-rebond (~800 ms, EXPERIENCE) avec la dernière `version` reçue. Le serveur ne fusionne jamais champ à champ. Au plus un `PUT` en vol par entrée : une frappe pendant un `PUT` met le dernier corps en file (il remplace le précédent en file), envoyé dès la réponse avec la `version` renvoyée. Le client ne peut donc pas se mettre en conflit avec lui-même. Un 409 `conflit_version` (autre onglet) renvoie l'entrée à jour : le client garde la saisie à l'écran, signale « Enregistrement en échec : la fiche a été modifiée ailleurs » et propose « Garder ma version » (renvoi du corps avec la `version` reçue) ou « Recharger » (affiche l'entrée du serveur). Un 503 ou une erreur réseau est réessayé après 3 s, saisie conservée.
- **CVSS à la frappe :** le recalcul immédiat côté client est un aperçu. Le score et la sévérité qui font foi sont ceux que renvoie `PUT …/correction` (`domaine/cvss31`). Le JS peut calculer le score localement, mais il ne l'envoie jamais.
- **Export pendant un lot :** refusé tant que ce lot tourne (409 `lot_en_cours`, ou `lot_en_cours_externe` s'il tourne dans un autre processus). Il est permis pour un lot terminé, échoué ou interrompu.
- **[revue A17] Confirmation d'export final :** si `non_validees > 0`, l'UI demande confirmation avant `POST …/export` final (« 3 fiches ne sont pas validées. Elles seront exclues du rapport et listées en annexe comme « non validée ». Exporter quand même ? »).
- **[revue A4] Téléchargement :** le JS reçoit le docx en `Blob` et déclenche l'enregistrement par un lien `download` (URL `blob:` du même document, non soumise à `default-src`). Aucun GET n'écrit de fichier.

## 27. Exports final et brouillon, commande `exporter` — `application/export.py`, `adaptateurs/export_docx.py`, `interfaces/cli.py`

Ajouté le 2026-10-18 (v2, CAP-13, CAP-17).

- **Service :** `application/export.exporter_lot(config, id_lot: str, mode: Literal["final","brouillon"]) -> Path` :
  1. `dossier_lot_existant` **[revue A3]** (sinon `RefusRelecture("lot_inconnu")`) ;
  2. un lot incident donne `RefusRelecture("lot_incident")` : `workflow` selon la règle de `application/lots.py` (§30), donc aussi un lot incident v0.1.0 sans `lot.json` **[revue E18]** ;
  3. **[revue A13/E13]** un lot `en_cours` (verrou de ce processus, ou pid vivant d'un autre processus sans événement de fin, §30) donne `RefusRelecture("lot_en_cours")` ;
  4. `relecture.charger`, puis `rapport_export(etat, mode)` ; en `final`, aucune fiche → `RefusRelecture("aucune_fiche_validee")` ;
  5. `composition.creer_exporteur(config).exporter(rapport, chemin, OptionsExport(langue=etat.langue, mode=mode, non_validees=…))`.

  Renvoie `(chemin, nombre de fiches non validées)`. `chemin` = `var/sorties/<id>/rapport-<id>.docx` ou `brouillon-<id>.docx`, écrasé à chaque export. **[revue E19]** Le service tient un verrou par chemin cible (`threading.Lock` indexé par chemin résolu) et l'exporteur écrit dans un provisoire unique `.<nom>.<uuid4().hex>.partiel` avant `os.replace` : deux exports simultanés ne se mélangent pas. Le `rapport.docx` de fin de lot n'est pas touché.
- **Rendu (`ExportDocx`) :** structure du §17, libellés `LIBELLES[langue]` de `formats.md` (v2), adoptés par Anaël le 2026-10-18 ; les titres des références ne sont pas traduits.

| clé | fr | en |
|---|---|---|
| bandeau | `Démonstration — données fictives` | `Demonstration — fictitious data` |
| titre | `Rapport de constats` | `Findings report` |
| synthèse | `N° \| Titre \| Sévérité \| Score \| Statut` | `No. \| Title \| Severity \| Score \| Status` |
| rubriques | `Description`, `Impact`, `Recommandation`, `CVSS 3.1`, `Références`, `Statut`, `Traçabilité` | `Description`, `Impact`, `Recommendation`, `CVSS 3.1`, `References`, `Status`, `Traceability` |
| sévérités | `Aucune`…`Critique` (§17) | `None`, `Low`, `Medium`, `High`, `Critical` |
| statuts | `OK`, `À revoir` | `OK`, `To review` |
| annexe | `Annexe — notes écartées`, `Note \| Statut \| Motif` | `Appendix — excluded notes`, `Note \| Status \| Reason` |
| marque | `Non validée` | `Not validated` |
| validée | `Validée` | `Validated` |

- **Mode `lot` :** rendu v0.1.0 dans la langue demandée. `rapport.docx`, en français, reste identique à la v0.1.0.
- **Mode `brouillon` :** le titre de niveau 2 d'une fiche dont la note est dans `non_validees` devient `"{N}. {titre} — {marque}"`. La section `Statut` garde le statut de génération et ses motifs.
- **Mode `final` :** pas de marque. La section `Statut` porte `Validée` (`Validated`) sans les motifs de génération, et la colonne `Statut` de la synthèse aussi (décision d'Anaël, 2026-10-18).
- **Annexe :** les deux modes y listent les entrées écartées, y compris `lot_interrompu` (§25). **[revue A17]** En mode `final`, l'annexe liste aussi chaque fiche de `non_validees` : `Note` = nom de la note, `Statut` = `Non validée` (`Not validated`), `Motif` = `fiche non validée, exclue du rapport final` (`not validated, excluded from the final report`). L'annexe est présente dès qu'il y a une entrée écartée ou une fiche non validée.
- **CLI :** `waveaudit exporter LOT [--brouillon] [--config F]`.
  - Charge la configuration, puis tout le reste sous `garde(...)`.
  - Mode `final` par défaut, `brouillon` avec `--brouillon`.
  - Affiche le bandeau français en première et dernière ligne, puis `rapport : <nom de fichier> (lot <id>)` ; en mode final, **[revue A17]** une ligne `fiches non validées : <n> (exclues, listées en annexe)` quand `n > 0`.
  - Codes : 0 ; 2 pour `lot_inconnu`, `lot_incident`, `lot_en_cours` **[revue A13]**, `aucune_fiche_validee`, `ConfigurationInvalide` (thème invalide) ; 4 pour `PermissionError` (« fermez le document dans Word ») et toute autre erreur.
  - Aucune commande CLI ne valide une fiche.
- **`composition.creer_exporteur(config) -> Exporteur`** (nouveau) : `ExportDocx(config.chemins.theme_prive)`, seul point d'instanciation hors `ouvrir`.

## 28. Thème de l'interface — `interfaces/web/static/`, `interfaces/web/templates/`

Ajouté le 2026-10-18 (v2, CAP-15).

- **`static/tokens.css`** (nouveau, versionné, public) : propriétés CSS sur `:root`, une par token de `DESIGN.md` :
  - couleurs : `--couleur-<nom>`, où `<nom>` est la clé YAML de `colors` (`primaire`, `accent-texte`…), valeurs exactes de `DESIGN.md` ;
  - focus : `--focus-contour`, `--focus-decalage` ;
  - typographie : `--police-texte`, `--police-chasse-fixe`, `--taille-<niveau>`.

  `style.css` n'utilise que ces propriétés pour les couleurs. Aucune `@font-face`, aucun `url()` hors `/static/` ou `/theme/`.
- **Logo :** `GET /theme/logo.svg` sert `config.chemins.theme_prive / "web" / "logo.svg"` s'il existe (relu à chaque requête, `FileResponse`), sinon 404.
  - Les gabarits reçoivent `logo_present: bool`, calculé à chaque rendu par `is_file()`. Ils n'affichent `<img src="/theme/logo.svg" alt="">` que si le fichier existe.
  - Aucun autre fichier de `theme-prive/` n'est servi. `theme-prive/web/theme.css` n'existe plus.
- **Tests :**
  - aucune URL `http://` ou `https://` hors `127.0.0.1` dans `templates/` et `static/` (test v0.1.0, étendu à `tokens.css`) ;
  - CSP présente sur `/`, `/lots/{id}` et `/incidents/{id}` ;
  - logo servi seulement si le fichier existe (deux `theme_prive` sous `tmp_path`) ;
  - bandeau en haut et en bas de chaque page ;
  - rôles ARIA : `listbox`/`option` du tiroir, `tablist`/`tab`/`tabpanel` des candidats, `dialog` des confirmations, d'après EXPERIENCE (analyse du HTML rendu) ;
  - **[revue V2] contrastes** : `tests/unitaires/test_contraste.py` lit `static/tokens.css` et la table « Rôle dérivé » et les ratios annoncés de `DESIGN.md`, recalcule chaque ratio WCAG 2.1 (luminance relative sRGB) pour chaque paire texte/fond déclarée, vérifie qu'il est `>= 4,5` pour un texte (`>= 3` pour un contour de focus ou un élément non textuel) et qu'il égale à 0,1 près le ratio écrit dans `DESIGN.md` ; une couleur de `tokens.css` différente de `DESIGN.md` fait échouer le test ;
  - **[revue V2] focus et ARIA** : `tests/accessibilite.py` (aide partagée) vérifie sur un HTML rendu que chaque élément interactif (`a[href]`, `button`, `input`, `select`, `textarea`, `[tabindex]`) a un nom accessible (`label for`, `aria-label`, `aria-labelledby` ou texte), qu'aucun `tabindex` n'est positif, que chaque `role="dialog"`/`alertdialog` porte `aria-modal="true"` et `aria-labelledby`, que les `id` référencés par `aria-*` existent ; et sur `style.css` qu'une règle `:focus-visible` utilise `--focus-contour` et qu'aucun `outline: none` n'est posé sans contour de remplacement. Appelée par `e2e/test_ui.py` (accueil, lots récents, suivi), `e2e/test_relecture_ui.py` (relecture) et `e2e/test_incident_ui.py` (incident).

## 29. Banc v2 — `application/banc.py`

Ajouté le 2026-10-18 (v2, CAP-5 à CAP-7 ; protocole `spec-waveaudit-v2/mesures-qualite.md`).

- **Signature :** `executer_banc(dossier, config, modele=None, langue=None, seed=None) -> Path`. Le lot reçoit `RequeteLot(..., langue=langue)` ; **[revue A31]** `seed` remplace `config.moteur.seed` par copie de configuration (CLI `banc --seed N`, défaut : la configuration).
- **`banc.json`** garde ses champs v0.1.0 et en ajoute :
  - `"langue"` ;
  - `"ok"` et `"a_revoir"` : nombre de fiches par statut de génération ;
  - `"recopie"` : moyenne non pondérée des valeurs ci-dessous, `null` sans fiche mesurable ;
  - `"recopie_par_rubrique"` : `{"titre","description","impact","recommandation"}`, moyenne par rubrique ;
  - `"replis"` **[revue A29]** : nombre de fiches portant `repli_sortie_invalide` ou `repli_moteur`, exclues de la recopie ;
  - `"seed"` : seed effective du lot ;
  - `"motifs"` : `{code: nombre}` sur toutes les fiches.
- **Recopie — définition unique [revue A29]**, celle de la référence 0,93 de `bilan-modeles.md` : pour chaque fiche qui n'est pas un repli et chaque rubrique R, `difflib.SequenceMatcher(None, fiche.R, textes.R).ratio()` avec `autojunk` à sa valeur par défaut (`True`), où :
  - `textes = catalogue.obtenir(fiche.tracabilite.constat_id).textes(langue)` ;
  - le texte de la fiche est le texte produit par le modèle tel qu'écrit dans `fiches.json` (c'est le « texte brut » de `bilan-modeles.md` : aucune normalisation, mêmes octets que ceux mesurés pour 0,93) ;
  - les replis (texte du catalogue par construction) sont comptés à part dans `replis`, jamais dans la moyenne.

  Le banc lit le catalogue par `composition.creer_catalogue(config)` (nouveau, `CatalogueYaml(config.chemins.catalogue)`).
- **Console :** une ligne de plus, `ok X/N, recopie 0,xx (titre … description … impact … recommandation …)`.
- **top1 / top3 :** inchangés dans `banc.json`. La mesure déterministe de CAP-5 (sans modèle) est `tests/unitaires/test_rattachement_demo.py`, qui devient bloquante : notes 01 et 29 au rang 1 ; 01 à 20 au moins 17/20 en top1 et 20/20 en top3 ; **[revue A30]** notes « non vues » 21 à 28 et 30 (la note 29, cible du réglage, en sort) au moins 8/9 en top1 et 9/9 en top3. Pendant la story de rattachement, le test des notes non vues est marqué `xfail(strict=False)` et n'est pas lu ; le marqueur est retiré en fin de story, une seule fois, et les valeurs obtenues sont figées dans le message de commit. Un échec à ce moment ne relance pas le réglage : la story s'arrête et le signale à Anaël.
- **[revue A31] Rebanc CAP-6 et CAP-7 :** chaque modèle est mesuré sur 3 seeds (42, 142, 242 ; `banc --seed`). Critère `ok` de CAP-6 : sur chaque seed, 6/6 fiches `ok`, en ne décomptant pas une fiche dont les seuls motifs sont `repetition` ou `langue` et qu'une relecture à la main confirme dégénérée ou dans une autre langue (consigné dans `bilan-modeles.md`). Recopie de CAP-6 et seuils de CAP-7 : sur la médiane des 3 seeds. `bilan-modeles.md` publie, par modèle, le minimum et la médiane de `ok`, la médiane et le maximum de la recopie.

## 30. Fiche d'un lot et liste des lots — `application/lots.py`

Ajouté le 2026-10-18 (v2, CAP-9, CAP-10).

- **`var/sorties/<id>/lot.json`**, écrit une fois, par `lot.ecrire_fiche_lot(dossier, *, id_lot, workflow, langue, modele_demande)` (public, écriture atomique, sans effet si le fichier existe) : par la route web avant son 303 **[revue A2]**, sinon par `executer_lot` et `executer_incident` dès que le dossier de sortie existe. Contenu : `{"id_lot", "workflow": "fiches"|"incident", "langue": "fr"|"en"|null, "modele_demande": str|null, "cree_le": ISO 8601 avec fuseau, "pid": int}` ; **[revue A13]** `pid` = `os.getpid()` du processus qui exécute le lot (CLI ou UI).
- **`application/lots.py`** (lecture seule) :
  - `ResumeLot` (dataclass figée) : `id_lot, workflow, etat, total: int | None, langue, modele, cree_le, url` ;
  - `lister_lots(config, occupation: Occupation | None) -> list[ResumeLot]` ;
  - `etat_lot(config, id_lot, occupation, depuis=0) -> dict` (forme de `/lots/{id}/etat`).
- **Règles :**
  - **`workflow`** : `lot.json`, sinon `incident` si `incident.json` ou `rapport-incident.docx` existe (lot v0.1.0), sinon `fiches`.
  - **`etat`** : `termine` si le dernier événement de `journal.jsonl` est `lot_termine` ; `echoue` si c'est `lot_echoue` (`erreur = details.message`) ; `en_cours` si l'occupation courante porte ce lot (nature `fiches` ou `incident`) ; **[revue A13/E12]** `en_cours` aussi si `lot.json` porte un `pid` différent de celui du processus courant, que ce processus est vivant (`composition.processus_actif(pid, cree_le)` : psutil, processus existant et créé avant `cree_le`, pour écarter un pid réutilisé) et que le journal n'a pas d'événement de fin ; `interrompu` sinon (processus arrêté, ou lot de ce processus sans occupation ni fin). L'UI traite `interrompu` comme `echoue` (EXPERIENCE, State Patterns). `ResumeLot` porte `externe: bool` (en cours dans un autre processus).
  - **`total`** : celui de `lot_demarre`, sinon `None`. **`modele`** : `lot_demarre.details.modele`, sinon `modele_demande`.
  - **`url`** : `/lots/{id}` ou `/incidents/{id}`.
  - **Tri [revue E22] :** `cree_le` décroissant (lu dans `lot.json`, sinon horodatage de `lot_demarre`, sinon date de modification du dossier), puis `id_lot` décroissant ; au plus 50.
  - **Source :** `journal.jsonl` sur le disque, relu à chaque appel, qui remplace le registre en mémoire du §18. Une ligne illisible est ignorée (log).
- La CLI et l'UI n'écrivent rien d'autre dans `var/sorties/<id>/` que les fichiers listés dans ce contrat : `lot.json`, `journal.jsonl`, `fiches.json`, `relecture.json`, `rapport.docx`, `rapport-<id>.docx`, `brouillon-<id>.docx`, `banc.json`, `incident.json` et `rapport-incident.docx`, **[revue A32/E20]** plus leurs provisoires d'écriture atomique (`.<nom>.partiel`, ou `.<nom>.<hex>.partiel` pour les exports), qui ne subsistent pas après une écriture réussie ou un échec rattrapé. Un test (R2, X2) vérifie qu'aucun `.partiel` ne reste.
- `composition.journal_reconnu(nom: str) -> bool` (nouveau) délègue à `adaptateurs/journaux.router_journal(nom)`, le nom public de l'actuel `_router` : l'UI refuse un dépôt incident sans journal routé avant de créer le lot.
