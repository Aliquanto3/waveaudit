# État v2

Plan : `plan-v2.md`. États possibles : `à faire`, `en cours`, `intégrée <sha>`, `bloquée : raison`.

| Vague | Story | Titre | dev-story | État |
|---|---|---|---|---|
| 0 | S0 | Socle v2 | Opus | intégrée e0fa92b |
| 1 | Q1 | Nouvelle tentative seed + 1, balises neutralisées, repeat_penalty transmis | Sonnet | intégrée c63b766 |
| 1 | Q2 | Garde-fous v2 (seuils, URL de la note, répétition, langue) | Sonnet | intégrée ab6ea6d |
| 1 | R1 | Règles pures de relecture | Sonnet | intégrée 3ea74d7 |
| 1 | M1 | Verrou unique et moteur à la demande | Opus | intégrée 17e4353 |
| 1 | X1 | Rendu Word bilingue, modes final et brouillon | Sonnet | intégrée f976867 |
| 1 | W1 | Socle web (routeurs, CSRF, en-têtes, erreurs codées) | Opus | intégrée 6bb935f |
| 2 | Q3 | Catalogue bilingue et traduction des 50 constats ★ | Sonnet | intégrée 0016786 |
| 2 | W5 | Thème public et logo privé | Sonnet | intégrée 349dde3 |
| 3 | Q4 | Index BM25 bilingue, rattachement des notes 01 et 29 | Sonnet | intégrée b8a8483 |
| 3 | L1 | Langue du lot, de la CLI au Word | Sonnet | intégrée fc41074 |
| 4 | B1 | Banc v2 | Sonnet | intégrée 762a165 |
| 4 | R2 | Persistance de la relecture et lot.json | Opus | intégrée fc527cc |
| 5 | Q5 | Rebanc EliteBook, consigne et rôles ★ | Opus | intégrée 751ccab (granite défaut, arbitrage d'Anaël) |
| 5 | W2 | Accueil, lots récents, suivi lu sur le disque | Sonnet | intégrée 996ce74 |
| 6 | X2 | Service d'export et `waveaudit exporter` | Sonnet | intégrée 029561e |
| 6 | W4 | Incident dans l'UI | Sonnet | intégrée 61f0141 |
| 7 | W3a | API de relecture, régénération et export | Opus | en cours |
| 8 | W3b | Écran de relecture | Sonnet | à faire |
| 7 | LIB | Libellés par langue des statuts et motifs dans le Word (annexe des écartées, tous modes) | Sonnet | intégrée 1b72836 |
| 8 | ARR | Arrêt propre de l'UI (llama-server enfant, fermer(timeout)) | Sonnet | à faire |
| 8 | DOC | README et guide des testeurs | Sonnet | à faire |
| 8 | REC | Recette finale sur l'EliteBook ★ | avec Anaël | à faire |

★ : point d'arrêt humain (voir `plan-v2.md`).

## Mode d'exécution (décidé avec Anaël le 2026-10-18)

- **Ordonnancement par dépendances** plutôt que par vagues : une story part dès que ses dépendances (en-tête de `stories.yaml`) sont intégrées. Q3 part dès Q2, W5 dès W1, L1 sans attendre Q4, B1 et R2 dès L1, DOC en parallèle de W3b. Intégration toujours une à une, dans l'ordre des collisions de fichiers partagés. Suite complète après S0, puis toutes les 3 ou 4 intégrations et en fin d'exécution.
- **Push** de `main` autorisé après chaque story revue, intégrée et verte.
- **Moins de sollicitations** : la relecture des 10 constats de Q3 est asynchrone (liste ci-dessous, corrections à tout moment avant Q5). Après le rebanc Q5, le modèle par défaut est choisi par la règle mécanique de CAP-7 et consigné avec ses chiffres ; Anaël peut l'infirmer. Les écarts au contrat et les stories bloquées sont consignés ici sans arrêter l'exécution. Restent avec Anaël : REC, puis le tag et la release 0.2.0.
- **Coupure de session** (après la vague 4, puis avant REC) : l'orchestrateur s'arrête et propose `/clear` à Anaël ; sans réponse sous 30 min, il continue.

## Relecture de Q3 (10 constats tirés au hasard)

Constats tirés par Q3 (textes `en` dans `donnees/catalogue/*.yaml`) : AD-KERBEROASTING, AD-ADCS-ESC1, AUTRE-MFA-ABSENTE, CONFIG-DEBUG-ACTIF, CONFIG-CORS-DEBUG, CRYPTO-HACHAGE-FAIBLE, INFRA-IPMI-EXPOSE, INFRA-LLMNR-NBTNS, WEB-XSS-REFLECHI, WEB-SSTI. Le second avis (Haiku) les a relus sans contresens relevé. Relecture d'Anaël : à faire, corrections avant Q5.

## Écarts à arbitrer

- README : MiniCPM5 encore présenté comme repli (à réaligner par DOC). Repli qwen3.5-0.8b non essayé sur le vrai moteur (à vérifier en REC).
- X1 : dans un Word `en`, les `detail` des motifs (textes du domaine) et les codes bruts (`non_traitee`, `non_rattachee`, `vecteur_invalide`…) restent en français ; §23 ne compte pas les motifs parmi les effets de la langue. Accepter, ou prévoir une story de `detail` par langue.
- R1 : §25 dit que `modifier` fait `version + 1` sans exception, mais une correction identique ne doit rien changer. Consigne pour R2 : `modifier` n'écrit ni n'incrémente quand `operation(entree) == entree`.
- R1 : `cvss31.evaluer` (imposé par le contrat) accepte `CVSS:3.0/…` et les métriques temporelles.
- M1 : l'ouverture du moteur tient le verrou interne, donc `fermer()` attend une ouverture en cours ; à confronter à l'attente de 10 s du lifespan (E3) en W2. `utiliser("B")` pendant un usage sur « A » n'est pas gardé : la sérialisation repose sur VerrouUnique (W2).
- W1 : cinq codes d'erreur hors table §26 (`introuvable`, `methode_refusee`, `requete_invalide`, `erreur_http`, `erreur_interne`) ; `Cache-Control: no-store` partout sauf `/static/` ; 409 `lot_en_cours` sans `occupation` jusqu'à W2.
- Q2 : la comparaison de boucle à la source ignore la casse (contrat : « telle quelle ») ; côté incident, la source des étapes 5 et 6 inclut aussi les identifiants, IP et hachages reconnus légitimes ; `finditer` à la place de `re.search` pour ne pas masquer une boucle derrière une suite sans lettre.

- W5 : nouveau token `--couleur-blanc` hors DESIGN.md (seule exception du test de parité) ; vérification du focus stricte (§28 à la lettre) : `:focus:not(:focus-visible) { outline: none }` serait refusé, à garder en tête pour W3b et W4 ; `lxml` importé directement par `tests/accessibilite.py` (transitif via python-docx).
- Q4 : les mots-clés ajoutés à WEB-XSS-REFLECHI et WEB-SSTI reprennent des expressions des notes 01 et 29 (« navigateur jetable », « erreur 500 avec trace du moteur », « expression arithmétique dans un champ »). CAP-5 fait de ces notes les cibles du réglage, mais contrats §16 et la règle des stories 4 et D1 demandent des mots-clés génériques : les rangs 1 de 01 et 29 sont mesurés sur les notes qui ont servi au réglage. Rien n'a été changé (le protocole interdit un second réglage). Mesure : 01-20 top1 18/20, top3 20/20 ; non vues 8/9, 9/9. Retrait de « cross-site scripting » et « reflected xss » (compensé par en.titre).
- R2 : un `relecture.json` illisible lève une `ValidationError` ; aucun code d'API prévu (W3a ne doit pas le laisser sortir en 500 brut). §26 annonce 409 `generation_en_cours` pour `POST …/candidat`, mais avec l'ordre du §26 (verrou d'abord) une régénération en cours donne 409 `lot_en_cours`. Réécriture complète de `relecture.json` à chaque fiche (O(n²), 18 ms par fiche à 300 notes, négligeable).
- B1 (avant Q5) : une rubrique complétée par le garde-fou (`rubrique_completee`) compte 1,0 dans la recopie, conformément à §29 et mesures-qualite.md (définition A29). Cela pénalise, sans jamais l'avantager, un modèle qui laisse des rubriques vides ; le cas reste visible (`a_revoir`, `motifs`). Définition gardée telle quelle pour Q5.
- W2 : `fermer()` de M1 reste bloquant pendant une ouverture du moteur : l'arrêt de l'UI pendant le démarrage d'une régénération dépasse la borne de 10 s (E3). Accepter pour le POC, ou story `fermer(timeout)` sur M1. Report antérieur (v0.1.0) : arrêter l'UI pendant un lot tue le fil daemon sans son `finally`, le llama-server du lot peut rester orphelin (à vérifier en REC : `tasklist | findstr llama-server`). `date_creation_processus` ajouté dans `adaptateurs/memoire_psutil.py` (psutil réservé aux adaptateurs). La redirection 303 `/lots/{id}` → `/incidents/{id}` est faite par W2 dans `pages.py` ; le sens inverse reste à W4.
- Q5 (arbitré : granite défaut, voir « Arbitrages ») : la règle de CAP-7 donne qwen3-1.7b par défaut (médianes 6/6, recopie 0,45, 36,2 s ; granite 6/6, 0,56, 27,9 s), mais CAP-6 n'est pas tenu pour qwen3-1.7b : 5/6 à la seed 242 (note 11 en `repli_moteur`, délai de 180 s dépassé, charge du poste supposée, non démontrée ; rejeu non compté). Options : valider qwen3-1.7b, garder granite (tient CAP-6), ou rebancer la seed 242 poste au repos. Reports : README (DOC), `ram_min_defaut_go` à remesurer, repli qwen3.5 et MiniCPM5 non rebancés. Détail : `bilan-modeles.md` section v2, `revues/story-Q5.md`.
- X2 : `exporter_lot` prend `occupation` (mot-clé, `None` en CLI) pour refuser un lot en génération dans le même processus (§27 étape 3) ; la signature du §27 ne le porte pas, à ajouter à la prochaine révision du contrat.
- W4 : sélecteur fiches/incident ajouté à l'accueil (`index.html`, `accueil.js`, hors liste de fichiers de W4, sur décision de l'orchestrateur : sans lui l'incident n'était pas atteignable depuis l'UI, CAP-14). `[hidden]{display:none !important}` global dans `style.css`. REC : vérifier dans un vrai navigateur la bascule, un envoi de journaux et `aucun_journal_reconnu` (aucun test n'exécute le JS). Le rapport incident (`export_incident_docx.py`) écrit toujours `code : detail` (français, conforme §17).
- LIB : le Word `fr` reste strictement identique à la v0.1.0 (§27, §17, prouvé par comparaison au rendu de 8ec9079) ; seuls les Word `en` reçoivent des libellés. Les tables `MOTIFS_EN`, `STATUTS_ECARTES_EN`, `RUBRIQUES_EN` dépassent la table normative de §27 et `formats.md` : à reporter au contrat. En `en`, la valeur variable est omise pour `note_invalide`, `aucun_constat` et les replis.
- Test instable : `tests/e2e/test_ui.py::test_lot_nominal_20_notes_puis_telechargement` a échoué une fois dans la suite complète après Q3 (machine chargée, suite à 173 s), puis passé seul, avec `tests/e2e/` et dans une seconde suite complète (908). À surveiller ; dev-story de correction s'il récidive.
Suite complète après la vague 5 (W2 + Q5) : 994 verts. Après la vague 6 (X2 + W4) : 1027 verts.

## Arbitrages d'Anaël (2026-10-18)

1. Modèle par défaut : **granite reste défaut** (tient CAP-6 ; un délai dépassé en usage réel est pire qu'une recopie un peu plus forte). qwen3-1.7b reste `candidat`, choisissable à l'accueil. Rôles rééchangés sur la branche Q5 avant fusion.
2. Arrêt de l'UI : story **ARR** « arrêt propre » (tuer le llama-server enfant à l'arrêt, `fermer(timeout)` sur M1), après W3a et avant REC.
3. Word `en` (X1) : accepté si les `detail` et codes bruts ne paraissent qu'en brouillon ; s'ils paraissent dans le Word final, story de libellés par langue avant REC. Vérifié : l'annexe des entrées écartées les écrit dans tous les modes, final compris (`export_docx.py:305-309`, ex. `non_traitee | lot_interrompu : lot interrompu`) ; aucun test ne couvre final + écartées. D'où la story **LIB**.
4. Relecture des 10 constats de Q3 : faite par Anaël pendant la REC, sur le Word `en`.
5 à 14. Écarts Q4, R1 (×2), W1, Q2, B1, W5, README/repli, test instable : acceptés tels que recommandés. R2 : W3a renvoie une erreur codée (`relecture_illisible`) pour un `relecture.json` illisible, jamais un 500 brut ; 409 `lot_en_cours` gardé pendant une régénération (ordre du §26). Repli qwen3.5-0.8b essayé en REC ; README réaligné par DOC.

## Consignes d'intégration pour les stories suivantes

Détail dans `revues/story-R2.md` : W3a prend `Occupation("regeneration", id, index)` avant `demarrer_regeneration` (sans occupation) ; `modifier` et `charger` reçoivent `occupation=verrou.occupation()` ; 409 `lot_en_cours_externe`, 503 `ecriture_impossible`. W2 écrit `ecrire_fiche_lot` avec la langue résolue et passe par `relecture.charger`. X2 utilise `relecture.charger` et refuse l'export d'un lot en cours d'après `lots.py`.

W2 (détail dans `revues/story-W2.md`) : X2 lit l'état par `lots.etat_lot(config, id, None)`, refuse un lot `en_cours`, obtient le dossier par `dossier_lot_existant`. W4 reprend l'ordre de `routeurs/lots.creer_lot` (occupation provisoire incident, `definir`, `ecrire_fiche_lot(workflow="incident", langue=None)`, `await run_in_threadpool(moteur.fermer)`, fil daemon journalisé avec `liberer` en `finally`), redirige `GET /incidents/{id}` d'un lot de fiches en 303 vers `/lots/{id}`, passe `/incidents/{id}/etat` par `lots.etat_lot`, ne touche pas `pages.py`. W3a utilise `app.state.config`, `.verrou`, `.moteur` (`app.state.lots` n'existe plus) ; 409 `lot_en_cours_externe` si `etat_lot` donne `en_cours` sans que l'occupation locale porte le lot, `lot_en_cours` sinon ; `etat_lot` sur le lot visé.

X2 (détail dans `revues/story-X2.md`) : W3a appelle `exporter_lot(config, id, mode, occupation=request.app.state.verrou.occupation())` via `run_in_threadpool` → `(chemin, non_validees)` ; refus : `lot_inconnu`, `lot_incident` → 404 ; `lot_en_cours` → 409 `lot_en_cours` si l'occupation locale porte le lot, sinon `lot_en_cours_externe` ; `aucune_fiche_validee` → 409 ; `PermissionError` → 409 `export_verrouille` ; `type` invalide → 422 `type_invalide` avant l'appel ; succès : nom `chemin.name`, en final en-tête `X-Non-Validees`. `relecture.json` illisible → erreur codée `relecture_illisible` (arbitrage 6).

W4 (détail dans `revues/story-W4.md`) : W3b ajoute à la fin de `style.css` sans réécrire les blocs W4 (« Page incident », « Accueil ») ; pour un tiroir ou un onglet, basculer une classe plutôt que l'attribut `hidden` ; un nouveau formulaire de dépôt porte la classe `depot`.

## Bilan

À remplir en fin d'exécution.
