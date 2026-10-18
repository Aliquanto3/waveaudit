---
id: SPEC-waveaudit-v2
companions:
  - formats.md
  - mesures-qualite.md
  - ecarts-contrat.md
  - ../../planning-artifacts/ux/DESIGN.md
  - ../../planning-artifacts/ux/EXPERIENCE.md
  - ../spec-waveaudit-poc/SPEC.md
  - ../spec-waveaudit-cert/SPEC.md
  - ../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/ARCHITECTURE-SPINE.md
  - ../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
sources:
  - arbitrages.md
  - ../../implementation-artifacts/bilan-modeles.md
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# WaveAudit v2 — qualité des fiches, relecture dans l'UI, anglais, incident dans l'UI

## Why

**Douleur et opportunité.** La v0.1.0 tourne de bout en bout, mais le banc de l'EliteBook montre trois limites. Les fiches recopient le catalogue (recopie de 0,93 pour granite) ; les notes 01 et 29 sont rattachées au mauvais constat ; des sorties dégénérées ou dans une autre langue passent `ok`. La retouche se fait ensuite dans Word, sans la note sous les yeux. La v2 corrige d'abord la qualité, avant l'UI. Elle apporte ensuite la relecture et la validation des fiches dans l'UI (choix du candidat, correction, export des fiches validées), les fiches en anglais pour les rapports de ce type, et le workflow incident dans l'UI. Le but : montrer aux testeurs et au sponsor un parcours complet sans Word intermédiaire.

## Capabilities

- **CAP-1**
  - **intent:** Après une sortie invalide du moteur, la nouvelle tentative utilise une seed différente, pour ne pas reproduire la même sortie.
  - **success:** Un test avec le faux moteur vérifie que le second appel reçoit `seed + 1` et que le repli reste inchangé si ce second appel échoue aussi. La modification du port `Moteur` passe par une story de socle dédiée.
- **CAP-2**
  - **intent:** Une note ou un actif contenant `</note>` ou `</constat>` ne peut pas fermer les balises du prompt.
  - **success:** Un test injecte ces balises dans le corps et l'actif d'une note : le message utilisateur ne contient chaque balise fermante qu'une fois, à sa place, et le texte de la note reste lisible.
- **CAP-3**
  - **intent:** Les garde-fous des fiches cessent de pénaliser ce qui est juste et signalent ce qui est dégénéré.
  - **success:** Tests avec le faux moteur : (a) un titre de 5 caractères ou plus est gardé, mais une autre rubrique de moins de 20 caractères est complétée ; (b) une URL présente dans la note ou dans son actif n'est pas retirée, alors qu'une URL absente de la note et du catalogue l'est toujours ; (c) une rubrique faite d'une répétition jusqu'à la longueur maximale donne `a_revoir` avec un nouveau motif dédié.
- **CAP-4**
  - **intent:** Une fiche ou un récit d'incident qui n'est pas rédigé dans la langue demandée est marqué à revoir.
  - **success:** Tests avec le faux moteur : une fiche en anglais dans un lot `fr`, une fiche en français dans un lot `en`, une rubrique terminée par un texte dans une autre écriture, et un récit d'incident en anglais donnent chacun `a_revoir` avec un motif de langue. Les fiches et récits de démonstration dans la bonne langue restent `ok`. Aucun appel réseau.
- **CAP-5**
  - **intent:** La recherche classe le bon constat type en première position pour les notes 01 (XSS réfléchi) et 29 (SSTI), sans régression ailleurs.
  - **success:** Mesure déterministe sans modèle (`mesures-qualite.md`) : notes 01 et 29 au 1er rang ; notes 01 à 20 au moins 17/20 en top1 et 20/20 en top3 ; notes 21 à 28 et 30, non vues pendant le réglage (la note 29, cible du réglage, n'en fait pas partie), au moins 8/9 en top1 et 9/9 en top3. Le test des notes non vues reste en `xfail` pendant le réglage ; le verrou est levé une seule fois, en fin de story, et les valeurs sont figées dans le commit. Mesures faites sur les notes françaises ; l'index BM25 reste bilingue (CAP-8) quelle que soit la langue du lot en cours de rattachement.
- **CAP-6**
  - **intent:** Les fiches s'adaptent à la note au lieu de recopier le constat type, sans perdre en fiabilité.
  - **success:** `repeat_penalty` se règle dans `[moteur]`, l'adaptateur OpenAI le transmet (vérifié par un test avec le faux moteur). Avec la consigne révisée, le rebanc sur l'EliteBook, sur 3 seeds par modèle, donne pour granite et pour qwen3-1.7b une recopie médiane inférieure à 0,7 et, sur chaque seed, `ok` ≥ 6/6 hors motifs `repetition` et `langue` confirmés à la main (`mesures-qualite.md`). Le minimum et la médiane de `ok` et de la recopie sont consignés dans `bilan-modeles.md`. Un test `slow` rejoue le banc sur 2 notes et vérifie un plafond de recopie.
- **CAP-7**
  - **intent:** Les rôles des modèles reflètent les mesures : un repli fiable et le meilleur défaut mesuré.
  - **success:** Le manifeste donne le rôle de repli à qwen3.5-0.8b à la place de MiniCPM5. Le défaut reste granite, sauf si qwen3-1.7b atteint, au rebanc sur l'EliteBook (médianes sur 3 seeds), au moins 5/6 `ok`, une recopie inférieure à 0,6 et une médiane inférieure à 40 s par fiche. La décision est consignée avec ses chiffres.
- **CAP-8**
  - **intent:** Le consultant choisit, pour tout le lot, la langue du rapport : français (par défaut) ou anglais.
  - **success:** Le catalogue est bilingue (`formats.md`) et `catalogue verifier` refuse une entrée qui n'a pas ses textes dans les deux langues. Un lot `en` lancé en CLI et dans l'UI avec le faux moteur reçoit la consigne anglaise et le constat type en anglais, et produit un Word aux libellés anglais. Sans choix, le lot est en français, comme en v0.1.0. La traduction anglaise de chaque entrée (identifiants, références et URL inchangés, titre traduit) est faite par le développeur de la story qui l'introduit ; Anaël relit un échantillon de 10 constats avant fusion.
- **CAP-9**
  - **intent:** Depuis l'accueil de l'UI, l'utilisateur crée un lot (workflow, dépôt des fichiers, modèle parmi les modèles installés, langue pour les fiches), puis retrouve et reprend les lots récents.
  - **success:** Test HTTP avec le faux moteur : l'accueil ne propose que les modèles présents dans le manifeste et sur le disque, avec le défaut présélectionné. Le lot créé utilise le modèle et la langue choisis. Un second lot pendant le premier est refusé avec le message prévu par EXPERIENCE.md. La liste des lots récents renvoie chacun vers son suivi ou sa relecture. Relancer des notes crée toujours un nouveau lot distinct ; les corrections et validations du lot d'origine restent intactes.
- **CAP-10**
  - **intent:** L'utilisateur suit l'avancement d'un lot de fiches et ouvre la relecture dès la première fiche prête.
  - **success:** Test HTTP : la progression ne recule jamais, le journal reçoit chaque événement, et une fiche terminée s'ouvre en relecture pendant que le lot continue. Sur un lot échoué, les fiches déjà produites restent relisibles et exportables, et les notes non traitées sont listées comme telles (EXPERIENCE.md, State Patterns corrigé).
- **CAP-11**
  - **intent:** Le consultant relit chaque fiche à côté de sa note et de ses 3 candidats, change de candidat pour régénérer la fiche, et peut générer la fiche d'une entrée non rattachée en lui choisissant un constat du catalogue.
  - **success:** Test HTTP avec le faux moteur : la relecture d'une fiche montre la note brute, les 3 candidats et la fiche. Le choix d'un autre candidat produit une nouvelle fiche sur ce constat type, garde-fous compris, et le candidat choisi est enregistré. Une entrée `non_rattachee` devient une fiche après le choix d'un constat dans une liste filtrable de tout le catalogue (ses candidats, à score nul, ne sont pas proposés). Si la fiche porte des corrections ou est validée, une confirmation précède son remplacement. La régénération redémarre `llama-server` à la demande s'il a été arrêté (après 5 min d'inactivité) ; elle est refusée (HTTP 409) si un autre lot tourne, même verrou que CAP-9.
- **CAP-12**
  - **intent:** Le consultant corrige une fiche (titre, description, impact, recommandation, vecteur CVSS, retrait de références) avec un enregistrement automatique, puis la valide.
  - **success:** Test HTTP : chaque correction est sur le disque et restituée telle quelle après rechargement, même après l'arrêt du serveur. Le score et la sévérité sont recalculés par le code depuis le vecteur saisi. Un vecteur invalide empêche la validation. Une référence ne peut être que retirée : aucun ajout n'est accepté. Une fiche validée puis modifiée repasse « à valider ». Deux onglets sur la même fiche ne perdent rien en silence : un conflit garde la saisie à l'écran et propose de garder sa version ou de recharger.
- **CAP-13**
  - **intent:** Le consultant exporte en Word soit le rapport final (fiches validées seulement), soit un brouillon (toutes les fiches, celles non validées marquées « non validée »).
  - **success:** Tests python-docx sur un lot où une partie des fiches est validée : le rapport final (`rapport-<id_lot>.docx`) ne contient que les fiches validées, dans leur version corrigée, avec le statut « Validée » (« Validated ») sans les motifs de génération ; les fiches non validées sont listées en annexe avec le statut « Non validée » (« Not validated »). L'UI demande confirmation avant l'export final s'il reste des fiches non validées. Le brouillon (`brouillon-<id_lot>.docx`) contient toutes les fiches, et chaque fiche non validée porte la mention « Non validée » (« Not validated » en anglais) dans son en-tête. Les deux documents gardent le bandeau et la structure du rapport (contrats §17), dans la langue du lot.
- **CAP-14**
  - **intent:** L'analyste lance le workflow incident depuis l'UI : choix du modèle parmi les modèles installés, dépôt des journaux, suivi, résultat (détections par sévérité, filtre, lecture de chaque détection) et téléchargement du rapport. Les récits ne sont pas éditables ; ils passent par le SLM choisi.
  - **success:** Test HTTP avec le faux moteur sur la démo CERT : l'UI propose le choix du modèle comme pour un lot de fiches (CAP-9), et le parcours donne un rapport `.docx` dont le contenu (sections, chronologie, détections, indicateurs) est le même que celui de `waveaudit incident` sur le même dépôt. Le résumé compte les 16 détections de l'oracle. Un dépôt sans détection affiche « Aucune détection sur ce dépôt » et le rapport reste téléchargeable.
- **CAP-15**
  - **intent:** L'UI suit DESIGN.md et EXPERIENCE.md : palette Wavestone publique, logo privé facultatif, bandeau de démonstration non masquable en haut et en bas, accessibilité WCAG 2.1 AA, usage complet au clavier, aucune ressource externe.
  - **success:** Des tests vérifient le bandeau sur chaque page, l'absence d'URL externe dans les gabarits et les fichiers statiques, la CSP `default-src 'self'`, le logo servi seulement si `theme-prive/web/logo.svg` existe, et les rôles ARIA des tiroirs, onglets et boîtes de dialogue. Un test unitaire recalcule les ratios de contraste des paires de `tokens.css` et les compare à DESIGN.md ; des tests sur le HTML rendu vérifient noms accessibles, ordre de tabulation, dialogues et focus visible. Une revue manuelle couvre au clavier les parcours 1 et 2 d'EXPERIENCE.md et confirme les contrastes listés dans DESIGN.md.
- **CAP-16**
  - **intent:** Le contrat normatif décrit le code livré.
  - **success:** Chaque écart de `ecarts-contrat.md` figure dans `contrats.md`, amendé par l'architecture. `lot.py` expose sous des noms publics ce qui était `_ID_LOT`, `_Emetteur`, `_sans_chemin` et `_sorties`, et plus aucun module hors `lot.py` n'importe un nom privé de `lot.py`.
- **CAP-17**
  - **intent:** Le consultant exporte en CLI le rapport final ou le brouillon d'un lot déjà relu, sans que la validation des fiches ne quitte l'UI.
  - **success:** `waveaudit exporter <lot>` produit `rapport-<id_lot>.docx` (fiches validées) ; `waveaudit exporter <lot> --brouillon` produit `brouillon-<id_lot>.docx` (toutes les fiches, mention « non validée » sur les fiches `a_valider`). L'export final affiche le nombre de fiches non validées (listées en annexe). Un lot inconnu, un lot en cours (y compris dans l'UI) ou un lot sans fiche validée (export final) donne un code d'erreur documenté. Aucune commande CLI ne valide une fiche.

## Constraints

- Les contraintes de SPEC-waveaudit-poc et SPEC-waveaudit-cert restent valables : pas de génération ex nihilo, garde-fous déterministes, moteur interchangeable par l'API OpenAI, SLM de moins de 2B, le SLM ne décide pas de ce qui est suspect. La v2 lève seulement ce que la spec nomme : français seul, édition hors UI, CERT en CLI seul. La charte quitte aussi le dépôt privé : la palette Wavestone devient publique (décision d'Anaël), seul le logo reste dans `theme-prive/`.
- Serveur sur `127.0.0.1` ou `::1` seulement ; aucun appel sortant à l'exécution, garde réseau actif ; aucune ressource externe dans l'UI (pas de CDN ni de police téléchargée).
- Poste cible : Windows 11 sans droits admin, 16 Go, CPU seul ; Edge ou Chrome, de 1366 à 1920 px de large.
- Le socle AD-0 ne se modifie que dans une story dédiée (CAP-1 et CAP-16). Seule modification de comportement de cette story : le modèle de repli (CAP-7). Deux exceptions, sur des valeurs seulement : la story de rattachement (CAP-5) peut régler `k1` et `b` de la recherche ; la story de rebanc (CAP-6, CAP-7) peut changer le rôle, `repeat_penalty` et la durée indicative des modèles existants du manifeste.
- Les commandes CLI de la v0.1.0 et leurs codes retour restent inchangés ; on ne fait qu'ajouter des options ou des sous-commandes.
- Un seul lot à la fois, fiches et incident confondus (verrou applicatif, HTTP 409). Le verrou est propre au processus UI : un lot CLI lancé pendant un lot UI peut charger un second llama-server (accepté par Anaël, documenté dans le README). Un lot consigne le processus qui l'exécute : tant que ce processus vit et que le lot n'est pas fini, l'UI le montre en cours et refuse de le modifier, et la CLI refuse de l'exporter.
- Données publiques ou fictives seulement. Les tests n'utilisent ni le vrai modèle ni le réseau, hors marqueur `slow`. Les mesures de qualité et de durée se font sur l'EliteBook.
- La traduction du catalogue est rédigée et versionnée dans le dépôt : rien n'est traduit à l'exécution.

## Non-goals

- Imports Burp et Nessus ; journaux EVTX (v3).
- Workflows scripts et défense : ils rouvriraient les décisions 4 et 8 du forge (passer par `bmad-correct-course`).
- Édition des récits d'incident ; choix de la langue du rapport d'incident (le choix du modèle, lui, est dans l'UI — CAP-14).
- Validation de fiches en CLI (CAP-17 n'exporte que ; la validation reste UI seule).
- Usage multi-utilisateur ou serveur, mobile.
- Logo ou modèle Word de marque dans le dépôt.
- Fine-tuning ; données client réelles ; traduction automatique du catalogue à l'exécution.

**Cadrage rouvert** (non-goals de spec seulement, aucune décision verrouillée du forge) : POC l.75 « Fiches en anglais » (CAP-8) ; POC l.77 « Édition des fiches dans l'UI » (CAP-11 à CAP-13) ; CERT l.53 « Interface web pour le CERT » (CAP-14).

## Success signal

- Sur l'EliteBook, Camille dépose les 6 notes du banc dans l'UI, relit les fiches, corrige au moins une fiche, change le candidat d'au moins une autre, valide, puis exporte le Word des fiches validées. Les mesures du rebanc (CAP-5 à CAP-7) sont consignées dans `bilan-modeles.md`. Karim déroule le parcours incident dans l'UI sur la démo CERT et télécharge le rapport. La suite complète et la CI sont vertes.

## Assumptions

- La langue du lot est celle des sorties (fiches, libellés Word). Les notes peuvent être rédigées dans l'une ou l'autre langue.
- Le rapport d'incident reste en français en v2 : le garde-fou de langue des récits vérifie le français.
- Seules les entrées `non_rattachee` peuvent être générées depuis l'UI ; une note invalide (`non_traitee`) ne le peut pas.
- Le « lot complet » de CAP-6 est le sous-ensemble de 6 notes du banc, avec le statut de chaque fiche mesuré.
- MiniCPM5 perd le rôle de repli ; son maintien comme candidat ou son retrait du manifeste relève de l'architecture.

## Open Questions

Aucune : les dix questions ouvertes de ce cadrage ont été tranchées par Anaël (2026-10-18, voir `.memlog.md`) et sont devenues des décisions, reflétées ci-dessus et dans `formats.md`. La relecture adversariale du 2026-10-18 (`revue-adversariale.md`, section Intégration) est intégrée.
