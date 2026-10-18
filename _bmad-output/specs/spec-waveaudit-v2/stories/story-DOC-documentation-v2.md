---
id: DOC
title: Documentation v2 (README et guide des testeurs)
status: review
sources:
  - ../stories.yaml
  - ../SPEC.md
  - ../../../planning-artifacts/ux/EXPERIENCE.md
  - ../../../implementation-artifacts/etat-v2.md
  - ../../../implementation-artifacts/bilan-modeles.md
  - story-W2-accueil-lots-recents.md
  - story-W4-incident-dans-l-ui.md
  - story-LIB-libelles-word.md
  - story-ARR-arret-propre.md
  - story-Q5-rebanc-elitebook.md
  - story-X2-export-waveaudit-exporter.md
---

# Story DOC — Documentation v2 (README et guide des testeurs)

Pas de code. Met à jour `README.md` et `docs/guide-testeurs.md` (le guide vit sous `docs/`,
pas à la racine : c'est l'emplacement réel du fichier, déjà lié par le README existant — voir
Écarts).

## Livré

### `README.md`

- **Installation / UI** : mention des deux workflows de l'accueil (fiches / incident, W4) et
  du choix de modèle et de langue (fr/en) au dépôt.
- **CLI** : tableau des commandes aligné sur `waveaudit --help` réel (ajout de `exporter`,
  resté absent du tableau) ; options `--langue` documentées pour `fiches` et `banc` (absente
  d'`incident`, qui reste toujours en français, EXPERIENCE Flow 2) ; `exporter LOT
  [--brouillon] [--config F]` (contrats §27, pas d'option `-o`, vérifié par
  `waveaudit exporter --help`).
- **Codes retour** (nouveau, vérifié contre `src/waveaudit/interfaces/cli.py`) : 0 lot
  terminé, 2 entrée/configuration invalide, 3 moteur injoignable, 4 connexion interdite ou
  permission refusée, 5 empreinte d'artefact invalide.
- **Incident dans l'UI** : refus d'un dépôt sans journal reconnu (message
  `aucun_journal_reconnu`), pas de choix de langue pour ce workflow.
- **Choix et licences des modèles** : table réécrite avec les rôles retenus par l'arbitrage de
  Q5 — `granite-4.0-1b` modèle par défaut (CAP-6 tenu : 6/6 sur 3 seeds, recopie médiane 0,56,
  médiane 27,9 s/fiche), `qwen3-1.7b` candidat (choisissable à l'accueil ; recopie 0,45, 36,2 s,
  mais 5/6 sur une seed par délai dépassé — CAP-6 non tenu), `qwen3.5-0.8b` modèle de repli
  (RAM basse, non rebancé en v2), `minicpm5-1b` candidat (non rebanché en v2). Retrait de toute
  mention de MiniCPM5 comme repli : il n'a jamais ce rôle en v2 (`config/artefacts.toml`).
  `repeat_penalty = 1.1` (granite et qwen3-1.7b) ; renvoi à `bilan-modeles.md` pour le détail du
  rebanc.
- **Mesure Q4** (nouveau, dans la section catalogue/mesure) : le rang 1 des notes 01 et 29 est
  mesuré sur des notes qui ont servi au réglage des mots-clés (optimiste) ; sur les notes non
  vues du banc, 8/9 et 9/9.
- **Preuve hors ligne / Contenu du dépôt** : logo et modèle Word de marque dans
  `theme-prive/web/logo.svg` (ignoré par git, absent du dépôt public), palette publique
  autrement.
- **Limites du POC** (complétées, sans retrait des limites existantes) : un lot CLI lancé
  pendant un lot UI peut charger un second llama-server (pas de verrou inter-processus en v2) ;
  le moteur est relancé à la première régénération après un lot ; le rapport d'incident reste
  en français seulement (ses codes bruts `code : detail` restent en français dans son annexe,
  y compris sur un Word `en`, LIB ne couvrant que le rapport de fiches) ; un lot CLI en cours
  est en lecture seule dans l'UI et refusé par `waveaudit exporter` ; les fiches non validées
  d'un lot sont listées en annexe du rapport final ; l'arrêt de l'UI (Ctrl+C) arrête proprement
  le llama-server enfant et marque un lot en cours `interrompu` (ARR).

### `docs/guide-testeurs.md`

- Section langue (fr/en) et choix du modèle à l'accueil, avec le modèle par défaut et son
  ordre de grandeur de durée (~28 s/fiche, granite).
- Parcours de Camille (adapté d'EXPERIENCE Flow 1), en étapes numérotées avec le résultat
  attendu à chacune : dépôt de 6 notes du banc (`donnees/demo/notes`, un sous-ensemble),
  relecture d'une fiche, correction d'une fiche, changement de candidat sur une autre entrée,
  une entrée non rattachée rattachée à la main depuis le catalogue, validation des fiches,
  export final puis export d'un brouillon (une fiche laissée non validée).
- Parcours de Karim (adapté d'EXPERIENCE Flow 2) : démo CERT dans l'UI
  (`donnees/demo/incident`), résumé par sévérité, filtre sur une carte, téléchargement du
  rapport ; dépôt sans journal reconnu → message `aucun_journal_reconnu`, aucun lot créé.
- Les deux parcours se font au clavier (`Tab`, flèches dans le tiroir et les onglets de
  candidats, `Ctrl+Entrée` pour valider, `Ctrl+Alt+↓`/`↑` pour naviguer, `Échap` pour fermer un
  dialogue).
- Nouvelle section **« Points à vérifier en recette »** : bascule fiches/incident et message
  `aucun_journal_reconnu` ; parcours clavier complet de la relecture (tiroir, onglets,
  raccourcis, dialogues) ; repli du tiroir sous 1440 px ; attribut `lang` du panneau de
  relecture en anglais sur un lot anglais ; confirmations (changement de candidat sur fiche
  corrigée ou validée, export final avec fiches non validées) ; arrêt de l'UI (Ctrl+C) pendant
  un lot en cours puis `tasklist | findstr llama-server` sans résultat ; repli sur
  `qwen3.5-0.8b` avec peu de RAM disponible ; relecture des 10 constats traduits de Q3 (liste
  dans `etat-v2.md`, « Relecture de Q3 ») sur un rapport Word `en`.
- Aucune capture d'écran ajoutée (aucune ne contiendrait de donnée réelle, cohérent avec
  l'existant).

## Vérifications faites

- `uv run waveaudit --help`, puis `--help` de `fiches`, `banc`, `exporter`, `incident`, `ui`,
  `installer` : options et absence d'options confirmées (pas de `--langue` sur `incident`, pas
  de `-o` sur `exporter`).
- Codes retour relus dans `src/waveaudit/interfaces/cli.py` (docstring de module et
  `_codes_retour`).
- Rôles des modèles relus dans `config/artefacts.toml` (`role = "modele_defaut"` sur granite,
  `"modele_repli"` sur qwen3.5-0.8b, `"candidat"` sur qwen3-1.7b et minicpm5) et dans
  `bilan-modeles.md` (§ v2, rebanc EliteBook Q5).
- Emplacement du logo privé relu dans `src/waveaudit/interfaces/web/routeurs/theme.py`
  (`theme-prive/web/logo.svg`).
- Parcours de Camille et de Karim relus dans `EXPERIENCE.md` (Flow 1 et Flow 2), écran de
  relecture dans `story-W3b-ecran-relecture.md` (branche `worktree-agent-a28d5fa75d62efb90`,
  absente de `main`).

## Écarts

- La consigne situe `guide-testeurs.md` « racine du dépôt » ; le fichier réel, déjà lié par le
  README (« Vous testez le POC ? »), est `docs/guide-testeurs.md`. Gardé à son emplacement
  réel plutôt que déplacé ou dupliqué, pour ne pas casser ce lien ni créer deux versions : un
  déplacement est hors périmètre d'une story de documentation sans changement de structure
  demandé ailleurs.
- `incident` connaît bien `--annee` (option avec valeur par défaut « année courante » quand
  l'option est omise, `cli.py`) ; déjà exact dans le README existant, revérifié, non modifié.
  [revue DOC] Formulation précédente ambiguë, lue comme « incident ne connaît pas --annee », ce
  qui est faux ; corrigée.

## Revue

- high | second avis | guide étape 2 de Camille disait ouvrir la relecture dès la première fiche prête, contredit `relecture.js` (ouverture seulement quand le lot n'est plus `en_cours`) | corrigé | reformulé sur le comportement réel.
- high | second avis | README/guide : libellés et raccourcis de l'écran de relecture (tiroir, candidats, `Ctrl+Alt+↓`, « Exporter un brouillon », « Enregistré ») écrits avant W3b | vérifié conforme | chaque libellé et raccourci retrouvé à l'identique dans `relecture.js`/`lot.html`, aucune correction de texte nécessaire au-delà du constat ci-dessus.
- medium | second avis | README « rang 1 atteint 8 fois sur 9 et 9 fois sur 9 » confondait top1 et top3 | corrigé | distingue désormais top1 = 8/9, top3 = 9/9 (`bilan-modeles.md`).
- medium | second avis | guide étape 4 de Karim proposait un dossier vide ou un `.csv` (reconnu) comme journal non reconnu | corrigé | remplacé par `notes.txt`, vérifié non reconnu par `journal_reconnu`.
- medium | second avis | guide étape 1 de Karim faisait déposer un dossier alors que le champ est un sélecteur de fichiers multiple | corrigé | étape reformulée, fichiers listés.
- medium | second avis | guide étape 5 de Camille supposait une note non rattachée dans le jeu de démo, alors qu'aucune des 30 notes ne le donne (`test_les_30_notes_de_demonstration_sont_rattachables`) | corrigé | étape reformulée pour ajouter une note hors sujet reproductible.
- low | second avis | libellés « Génération en cours », « Enregistrement… », « Exporter un brouillon » à vérifier | vérifié conforme | aucune correction.
- low | second avis | limites manquantes : borne d'arrêt UI non garantie à 10 s hors Windows, régénération dans une autre instance non détectable | corrigé | deux puces ajoutées à « Limites du POC ».
- low | second avis | seuil de repli modèle (RAM ≥ 4,5 Go) absent du README | corrigé | phrase ajoutée, seuil non remesuré en v2 noté.
- low | second avis | spec DOC:113 « incident ne connaît pas --annee » faux | corrigé | reformulé ci-dessus.
- — | reviewer | « Points à vérifier en recette » du guide incomplète au regard de `revues/story-W3b.md` | corrigé | puces ajoutées sans doublon (Enregistrement…/Enregistré et `aria-live`, conflit à deux onglets, serveur arrêté pendant une saisie, confirmation de changement de candidat détaillée, export brouillon par `Blob`, lien « Télécharger le rapport », opacité des dialogues, piège de focus Tab).
- — | reviewer | Complexité | — | 0 constat (story de documentation seule, aucune structure de code modifiée).
