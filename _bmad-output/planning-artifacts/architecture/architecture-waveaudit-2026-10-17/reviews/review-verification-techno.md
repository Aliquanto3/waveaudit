# Revue — vérification des affirmations de comportement (techno)

Date : 2026-10-17. Portée : ARCHITECTURE-SPINE.md (hors table Stack/SHA-256, déjà vérifiée aujourd'hui). Sources : README `tools/server` et code `tools/server/server-common.cpp` de `ggml-org/llama.cpp` via `gh api`, dépôt `RedHatProductSecurity/cvss` (tag v3.6), dépôt `miketheman/pytest-socket` (source + issues), release-notes FastAPI, recherche web pour le reste.

## 1. llama-server b11714 — `/v1/chat/completions`, `response_format.json_schema`, flags

**Statut : confirmé, avec une nuance sur `strict`.**

- `response_format` de type `json_schema` : confirmé. Le code (`tools/server/server-common.cpp`, ~l. 1302-1326) reconnaît explicitement `response_type == "json_schema"`, lit `response_format.json_schema.schema` (forme imbriquée façon OpenAI) et l'utilise comme grammaire JSON contrainte. Pas d'erreur levée pour ce type.
- Le champ `strict` (et `name`) du sous-objet `json_schema` : **n'est lu par aucun code** — seul `schema` est extrait de `schema_wrapper`. `strict: true` est donc accepté syntaxiquement (pas d'erreur) mais **n'a aucun effet** : la contrainte vient entièrement du décodage par grammaire (déjà strict par construction), pas d'un commutateur `strict`. AD-3 affirme implicitement que `strict` configure un comportement ; en réalité c'est un no-op côté serveur.
  - **Correction proposée (spine, AD-3)** : préciser que `strict: true` est transmis par compatibilité avec le format OpenAI mais ignoré par llama-server (le JSON Schema est de toute façon appliqué strictement via grammaire).
- `--no-webui` : confirmé, alias documenté (`--ui, --webui, --no-ui, --no-webui`, défaut : activé) — README `tools/server/README.md` l. 210.
- `--jinja` : confirmé, existe et est documenté (`--jinja, --no-jinja`, défaut déjà activé) — l. 232. Le passer explicitement est donc sans risque mais redondant avec le défaut actuel de ce build.
- `--parallel` (`-np`) : confirmé — l. 177.
- `/health` : confirmé, endpoint public sans clé API, `GET /health` (et alias `/v1/health`) — l. 477-479.

Source : `gh api repos/ggml-org/llama.cpp/contents/tools/server/README.md` et `.../server-common.cpp` (branche par défaut, lus ce jour).

## 2. Support modèles granite-4.0-1b et MiniCPM5-1B, variante dense vs hybride

**Statut : confirmé.**

- `granite-4.0-1b` est bien l'architecture **dense** (`GraniteForCausalLM`), distincte de la famille hybride `granite-4.0-h-*` (`GraniteMoeHybridForCausalLM`, Mamba-2/Transformer). Le nom retenu dans le manifeste (`granite-4.0-1b-Q4_K_M`, sans `-h-`) correspond donc bien au modèle dense, pas à la variante hybride. Le support hybride dans llama.cpp est plus récent/fragile (une discussion antérieure notait l'absence de support pour `granite-4.0-tiny-preview` avant l'architecture `granitehybrid`) — bonne raison supplémentaire d'avoir choisi le dense pour un POC.
- `MiniCPM5-1B` : confirmé supporté nativement. Le dépôt officiel `openbmb/MiniCPM5-1B-GGUF` indique une architecture `LlamaForCausalLM` standard (pas de code custom requis), avec quantisations F16/Q8_0/Q4_K_M, et la documentation OpenBMB recommande explicitement llama.cpp « vanilla » pour CPU/edge.
- **Non vérifiable précisément** : aucune source ne donne le build minimal exact de llama.cpp supportant MiniCPM5-1B ; b11714 (récent, octobre 2026) est vraisemblablement suffisant mais ce point reste à confirmer par un test réel (déjà prévu via le test `slow`).

Sources : recherche web (fiche HF `openbmb/MiniCPM5-1B-GGUF`, doc OpenBMB `minicpm5-deploy-llama-cpp`, table d'architectures IBM/gguf).

## 3. Bibliothèque `cvss` 3.6 — classe `CVSS3`

**Statut : confirmé.**

- Le tag `v3.6` existe dans le dépôt source (`RedHatProductSecurity/cvss`, qui publie le paquet PyPI `cvss`). La classe `CVSS3` y est définie (`cvss/cvss3.py`), avec des méthodes `scores()` et `severities()` retournant respectivement les scores et sévérités base/temporal/environmental.
- Vecteur invalide : lève `CVSS3MalformedError` (format incorrect, champ manquant, métrique dupliquée, etc.) ou `CVSS3MandatoryError` (métrique obligatoire absente) — toutes deux sous-classes de `CVSS3Error`/`CVSSError`, pas une exception générique.
  - **Correction proposée (spine, AD-5, point 3)** : nommer explicitement `cvss.CVSS3Error` (ou ses sous-classes `CVSS3MalformedError`/`CVSS3MandatoryError`) comme exception à capturer avant de retomber sur le vecteur par défaut, plutôt que de laisser entendre une levée d'exception non qualifiée.

Source : `gh api repos/RedHatProductSecurity/cvss/{tags,contents/cvss/cvss3.py,contents/cvss/exceptions.py}`.

## 4. `pytest-socket` 0.8.1 — `--allow-hosts` avec/sans `--disable-socket`, et serveur uvicorn en thread

**Statut : confirmé, configuration retenue par le spine saine.**

- `--allow-hosts` fonctionne **seul** (sans `--disable-socket`) : confirmé par le code (`_resolve_allow_hosts` → `socket_allow_hosts`), qui ne dépend pas de `disable_socket()`. Il ne fait que remplacer `socket.socket.connect`, pas la classe `socket.socket` elle-même.
- Point important trouvé en creusant : il existe un bug ouvert et non corrigé, **issue #540** sur `miketheman/pytest-socket` (créée le 2026-09-19, toujours ouverte au 2026-10-17, postérieure à la release 0.8.1 du 2026-08-19) : `disable_socket()` remplace `socket.socket` par `GuardedSocket`, dont `accept()` sur un socket d'écoute déjà ouvert lève `SocketBlockedError` (un `RuntimeError`, non intercepté par `socketserver.BaseServer.serve_forever`, qui ne capture que `OSError`) — un serveur lancé dans un thread (type uvicorn) **meurt silencieusement** si le run utilise `--disable-socket`.
- **Mais** : ce bug ne touche que le chemin `--disable-socket` (remplacement de la classe). La configuration réellement prévue par le spine (`--allow-hosts=127.0.0.1,::1`, **sans** `--disable-socket`) ne passe pas par `GuardedSocket` et n'est donc pas affectée. Le faux moteur FastAPI/uvicorn (AD-10) peut donc tourner dans un thread sans risque lié à ce bug, **à condition de ne pas ajouter `--disable-socket`** en plus de `--allow-hosts` dans `addopts`.
  - **Correction proposée (spine, AD-9)** : ajouter une note explicite « ne pas combiner avec `--disable-socket` » pour que personne n'« améliore » la configuration plus tard en pensant renforcer la garde, et casse le faux moteur en thread (issue #540 encore ouverte).

Sources : `gh api repos/miketheman/pytest-socket/{contents/README.md,contents/src/pytest_socket/__init__.py,issues/540,releases}`.

## 5. `cyclonedx-py environment` (paquet `cyclonedx-bom` 7.5.0)

**Statut : confirmé pour l'essentiel, flags exacts non vérifiés en détail.**

- La sous-commande `environment` (alias `env`, `venv`) existe dans la version 7.5.0 et génère un SBOM CycloneDX à partir de l'environnement Python installé — approche recommandée par la doc pour la précision.
- Sortie JSON : confirmée par défaut sur les versions 7.x (`--output-format`/`--of`, choix JSON/XML, JSON par défaut) ; la doc 7.5.0 elle-même illustre un exemple avec `--output-format XML`, ce qui confirme que l'option existe toujours à cette version. Écriture sur fichier via `--output-file` (défaut `-` = stdout).
- **Non vérifié en détail** : la liste complète des options de la version 7.5.0 précise (recherche web uniquement, pas de lecture directe du `--help` de cette version). La commande du spine (« `waveaudit sbom` écrit `var/sbom.cdx.json` via `cyclonedx-py environment` ») est plausible mais devra préciser `--output-file var/sbom.cdx.json` (et éventuellement `--of json` par explicite) lors de l'implémentation — à vérifier avec `cyclonedx-py environment --help` une fois le paquet installé (ne nécessite pas de réseau, test déterministe faisable en CI/local).

Source : recherche web (doc ReadTheDocs `cyclonedx-bom-tool` versions 7.1.0/7.5.0).

## 6. Job Object Windows via `ctypes` + `KILL_ON_JOB_CLOSE`, sans pywin32

**Statut : confirmé faisable, deux pièges à documenter.**

- Faisable sans pywin32 : pattern connu (ex. gist largement repris), `CreateJobObjectW` + `SetInformationJobObject(JobObjectExtendedLimitInformation, JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE)` + `AssignProcessToJobObject`, tout accessible via `ctypes.windll.kernel32`.
- **Piège 1 — handle du processus** : `AssignProcessToJobObject` a besoin d'un *handle* de processus avec les droits `PROCESS_SET_QUOTA | PROCESS_TERMINATE` (pas seulement le PID). `subprocess.Popen` sur Windows expose bien un handle interne (`Popen._handle`, attribut privé/non documenté de CPython), mais il est plus robuste d'ouvrir un nouveau handle propre via `ctypes.windll.kernel32.OpenProcess(PROCESS_SET_QUOTA | PROCESS_TERMINATE, False, popen.pid)` plutôt que de s'appuyer sur `_handle` (API interne susceptible de changer).
  - **Correction proposée (spine, AD-11)** : préciser « handle obtenu via `OpenProcess(pid)`, pas via l'attribut privé `Popen._handle` ».
- **Piège 2 — course à l'assignation** : si le job n'est pas marqué non héritable et que `AssignProcessToJobObject` est appelé après coup (ce qui est le cas ici : `Popen` démarre le processus avant l'appel), tout descendant lancé par `llama-server` *avant* l'assignation échapperait au job. Risque faible dans ce cas précis car `llama-server` ne spawn pas de sous-processus au démarrage, mais à documenter comme limite connue plutôt qu'absence de piège.

Sources : recherche web (billets Meziantou, Nikhil Marathe « Windows Job Objects for Process Tree Management », gist `ubershmekel/119697afba2eaecc6330`).

## 7. FastAPI 0.143 — `TestClient` (httpx), upload multipart (`python-multipart`)

**Statut : confirmé, pas de signal de rupture.**

- La version `0.143.3` existe bien et a été publiée le 2026-10-16 (veille de ce jour), avec `0.143.0` le 2026-10-08 — confirmé via les release-notes du dépôt `fastapi/fastapi`.
- `TestClient` basé sur `httpx` : toujours d'actualité (architecture inchangée depuis plusieurs années majeures de FastAPI/Starlette), aucune mention de rupture dans les notes de version consultées.
- `python-multipart` reste la dépendance requise pour parser les formulaires multipart (`UploadFile`) : confirmé par la documentation officielle FastAPI (inchangé).
- **Non approfondi** : pas de lecture exhaustive du changelog complet entre 0.141 et 0.143 pour écarter toute micro-rupture ; aucun indice trouvé en sens contraire, risque jugé faible pour un POC.

Sources : `gh api repos/fastapi/fastapi/contents/docs/en/docs/release-notes.md` ; doc FastAPI « Request Files ».

---

## Synthèse des corrections à reporter sur le spine

| AD | Correction |
| --- | --- |
| AD-3 | Préciser que `strict: true` dans `json_schema` est ignoré par llama-server (no-op côté serveur, la contrainte vient de la grammaire). |
| AD-5 | Nommer l'exception à capturer : `cvss.CVSS3Error` (ou `CVSS3MalformedError`/`CVSS3MandatoryError`). |
| AD-9 | Ajouter « ne jamais combiner `--allow-hosts` avec `--disable-socket` » (bug ouvert miketheman/pytest-socket#540 sur `accept()` en thread). |
| AD-11 | Préciser l'obtention du handle de processus via `OpenProcess(pid)` plutôt que l'attribut privé `Popen._handle` ; noter la limite connue (descendants lancés avant l'assignation au job échapperaient à `KILL_ON_JOB_CLOSE` — risque jugé négligeable pour `llama-server`). |
| AD-12 | Préciser les flags exacts de `cyclonedx-py environment` (`--output-file var/sbom.cdx.json`) à confirmer via `--help` à l'implémentation. |
