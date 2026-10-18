---
name: WaveAudit
status: final
sources:
  - _bmad-output/planning-artifacts/ux/.memlog.md
  - _bmad-output/specs/spec-waveaudit-v2/arbitrages.md
  - _bmad-output/planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
  - _bmad-output/specs/spec-waveaudit-cert/formats-incident.md
updated: 2026-10-18
---

# WaveAudit — Experience Spine

> Voie rapide. Application web de bureau, rendu serveur Jinja + JS sans framework, servie sur
> `127.0.0.1`. Paire avec `DESIGN.md` (tokens référencés en `{colors.primaire}` etc.). Maquette
> de l'écran de relecture : `mockups/relecture.html` — les spines priment sur la maquette en cas
> de conflit.

## Foundation

Application web de bureau, Windows 11, ouverte dans Edge ou Chrome, servie en local sur
`127.0.0.1` (garde réseau actif, pas d'accès externe). Portable 1366 à 1920 px de large, pas de
mobile. Pile : rendu serveur Jinja2 et JavaScript sans framework ni étape de build, toutes les
ressources locales, CSP `default-src 'self'`. `DESIGN.md` est la référence d'identité visuelle ;
cette spine porte le comportement. Un seul lot à la fois (verrou applicatif).

Deux workflows indépendants partagent l'en-tête, le bandeau de démonstration et le mécanisme
d'export : **fiches** (notes de pentest → rapport de constats) et **incident** (journaux → rapport
de détections CERT).

## Information Architecture

| Surface | Atteinte depuis | Route indicative | Rôle |
|---|---|---|---|
| Accueil | Ouverture de l'app | `GET /` | Choisir le workflow (fiches / incident), déposer les fichiers, choisir modèle et langue (fiches) |
| Lots récents | Lien depuis l'accueil | `GET /lots` *(nouveau, à confirmer)* | Reprendre un lot déjà lancé (`var/sorties/`) |
| Suivi d'un lot (fiches) | Redirection après dépôt, ou reprise | `GET /lots/{id}` | Barre de progression, journal d'événements, lien vers la relecture dès la première fiche prête |
| Relecture | Depuis le suivi, ou directement si le lot est terminé | `GET /lots/{id}` (même page, état « terminé ») | Tiroir de liste + note + candidats + fiche + export |
| Suivi d'un lot (incident) | Redirection après dépôt des journaux | `GET /incidents/{id}` *(nouveau, à confirmer)* | Barre de progression, journal d'événements |
| Résultat incident | Depuis le suivi incident, une fois terminé | `GET /incidents/{id}` (même page, état « terminé ») | Résumé des détections, liste, téléchargement du rapport |

Chaque surface listée est atteinte par un parcours (voir Key Flows). L'export du rapport de
fiches se fait depuis la Relecture (pas de surface séparée) ; le téléchargement du rapport
incident se fait depuis le Résultat incident.

→ Composition de référence : `mockups/relecture.html`, écran de relecture seul. Le reste de l'IA
est spécifié par cette spine sans maquette (voie rapide) ; spine gagne en cas de conflit.

## Voice and Tone

Français, vouvoiement, sobre. Chaque message d'erreur dit ce qui se passe et ce qu'il faut faire.
Jamais de chemin de fichier absolu affiché (contrats §18/C6b).

| Situation | Message |
|---|---|
| Fichier trop gros | « Ce fichier dépasse 1 Mo (`rapport-pentest-v3.md`, 2,4 Mo). Réduisez-le ou retirez-le du dépôt. » |
| Nom de fichier invalide | « Le nom « ../config.md » n'est pas accepté. Utilisez des lettres, chiffres, espaces, points ou tirets, en `.md` ou `.txt`. » |
| Lot déjà en cours | « Un lot est déjà en cours (lancé à 09:14). Attendez sa fin ou [reprenez-le](#). » |
| Moteur injoignable | « Le moteur de génération ne répond pas. Vérifiez qu'il est démarré, puis réessayez. » |
| Modèle absent | « Le modèle « qwen3-4b » n'est plus installé. Choisissez un autre modèle dans la liste. » |
| Enregistrement en échec | « La correction n'a pas pu être enregistrée. Dernière version conservée à l'écran ; nouvelle tentative dans quelques secondes. » |

Pas d'emoji, pas de ton enjoué. Les deux protagonistes (consultante, analyste CERT) sont traités
de la même façon.

## Component Patterns

Comportement ; les spécifications visuelles sont dans `DESIGN.md.Components`.

| Composant | Comportement |
|---|---|
| Bandeau démonstration | Toujours affiché, en haut et en bas de chaque page ; aucun bouton de fermeture ni de réduction (AD-14). Identique sur les deux workflows. |
| En-tête | Statique (pas de navigation ni de menu caché dedans). Le bloc `.lot` (nom du lot, nombre de notes, état) n'apparaît que sur les surfaces Suivi d'un lot et Relecture ; absent sur Accueil et Lots récents. |
| Carte de dépôt | Glisser-déposer ou clic pour ouvrir le sélecteur de fichiers du système. Chaque fichier accepté apparaît dans une liste avec un bouton de retrait avant envoi. Le dépôt est désactivé pendant l'envoi (fonction `POST /lots`). |
| Sélecteurs modèle et langue | Le modèle par défaut (`granite`, ou le modèle désigné défaut par la configuration) est présélectionné ; un modèle absent du manifeste n'apparaît pas dans la liste. La langue est fixée pour tout le lot dès le lancement, non modifiable ensuite. |
| Barre de progression du lot | Se met à jour par sondage de `GET /lots/{id}/etat?depuis=N` (contrats §18) ; avance fiche par fiche, jamais en arrière. |
| Journal d'événements | Ajoute une ligne par événement reçu (`fiche_demarree`, `fiche_terminee`, `fiche_non_rattachee`, …), le plus récent en bas, défilement automatique sauf si l'utilisateur a remonté manuellement. |
| Tiroir de la liste des fiches | Un clic sur une ligne ouvre cette fiche dans la relecture sans recharger la page. Liste au rôle `listbox` (`aria-label="Fiches du lot"`), chaque ligne au rôle `option` (`aria-selected`), focusable et activable au clavier (flèches haut/bas pour déplacer la sélection, `Entrée`/`Espace` pour ouvrir), pas seulement au clic. Le tiroir se replie/déplie via un bouton persistant (préférence non enregistrée entre sessions, voie rapide) et se replie automatiquement sous 1440px de largeur ou à 200% de zoom (DESIGN.md.Layout & Spacing). |
| Pastille de statut | Purement informative, jamais cliquable. Icône et libellé changent ensemble, jamais la couleur seule. |
| Barre des candidats | Rôle APG Tabs complet : conteneur `role="tablist"`, chaque onglet `role="tab"` + `aria-selected` + `aria-controls` vers le panneau de fiche, panneau en `role="tabpanel"`. Navigation par flèches gauche/droite entre onglets, `Entrée`/`Espace` ou clic pour activer. Cliquer ou activer un onglet relance la génération de la fiche sur ce candidat (11 à 36 s, bilan-modeles). Si la fiche courante porte des corrections non enregistrées, une boîte de confirmation précède le changement. Pendant la régénération, `aria-busy="true"` est posé sur le panneau de fiche, qui affiche « Génération en cours » en surimpression légère mais reste lisible et non éditable jusqu'au remplacement ; une annonce ponctuelle (`aria-live="polite"`) signale la fin de la génération. |
| Panneau note | Lecture seule, défilement indépendant de la fiche ; sert de référence constante pendant toute la relecture de cette entrée. |
| Formulaire de fiche | Chaque champ s'enregistre automatiquement après une pause de frappe (anti-rebond, voir Interaction Primitives). Modifier une fiche déjà validée la repasse au statut « à valider » et le signale par un bref changement visuel de la pastille. |
| Champ CVSS | Le score et la sévérité se recalculent immédiatement à la frappe, sans attendre l'enregistrement ; un vecteur invalide pose `aria-invalid="true"` sur le champ et affiche l'erreur sous le champ, liée par `aria-describedby`, sans bloquer la saisie. |
| Encart des motifs | Lecture seule, visible dès que la fiche est générée « à revoir », chaque motif marqué « signalé à la génération ». Reste affiché pendant la correction (y compris si les motifs ne s'appliquent plus) ; disparaît seulement à la validation de la fiche, jamais automatiquement avant. |
| Barre d'actions | « Valider » exige un CVSS valide ; désactivé sinon, raison donnée par un texte visible lié au bouton via `aria-describedby` (pas une seule info-bulle `title`). « Suivante » passe à la fiche suivante du tiroir sans changer son statut. « Exporter » n'inclut que les fiches validées ; « Exporter un brouillon » inclut tout, fiches non validées marquées « non validée » (voir Flow 1, étape brouillon). |
| Indicateur d'enregistrement | Passe de « Enregistrement… » à « Enregistré » environ une seconde après la dernière frappe ; reste discret, jamais en boîte de dialogue ; annoncé par `aria-live="polite"` (un seul message, pas une répétition par frappe). |
| Boîte de confirmation | Toujours deux boutons, le bouton destructeur n'est jamais pré-focalisé : le focus initial va sur le bouton « annuler ». Fermable par `Échap`. À la fermeture (annulation, confirmation ou `Échap`), le focus revient à l'élément qui a ouvert la boîte. |
| Page incident | Le résumé agrège par sévérité ; cliquer une carte de sévérité filtre la liste des détections en dessous. Le téléchargement démarre immédiatement au clic (pas d'étape intermédiaire), fichier `.docx`. |

## State Patterns

| Surface | État | Traitement |
|---|---|---|
| Accueil | Vide (premier lancement) | Carte de dépôt seule, pas de lot en cours ; lien « Lots récents » absent si `var/sorties/` est vide. |
| Accueil | Lot déjà en cours | Dépôt désactivé ; message « lot déjà en cours » avec lien (voir Voice and Tone). |
| Lots récents | Vide (`var/sorties/` vide) | Surface non atteignable : le lien « Lots récents » est absent de l'Accueil (voir État Accueil « vide »). |
| Lots récents | Liste | Un lot par ligne : nom/horodatage, nombre de notes, statut (en cours / terminé / échoué) ; clic reprend ce lot (`GET /lots/{id}` ou `/incidents/{id}` selon le workflow). |
| Suivi d'un lot (fiches) | En cours | Barre de progression + journal qui s'allonge ; aucune action possible sauf attendre. |
| Suivi d'un lot (fiches) | Terminé | Redirection douce vers la relecture (ou affichage direct si déjà sur la page). |
| Suivi d'un lot (fiches) | Échoué | Message d'erreur en haut (ex. moteur injoignable), journal conservé jusqu'à l'échec, pas de relecture possible pour ce lot. |
| Suivi d'un lot (incident) | En cours | Même traitement que fiches : barre de progression + journal, aucune action possible sauf attendre. |
| Suivi d'un lot (incident) | Terminé | Redirection douce vers le Résultat incident (ou affichage direct si déjà sur la page). |
| Suivi d'un lot (incident) | Échoué | Message d'erreur en haut (ex. dossier illisible), journal conservé jusqu'à l'échec, pas de résultat affiché pour ce lot. |
| Relecture | Génération d'une fiche (changement de candidat) | Fiche visible mais non éditable, mention « Génération en cours », remplacée automatiquement à la fin (succès ou repli garde-fou). |
| Relecture | Erreur | Bandeau d'erreur en haut de la fiche concernée ; les autres fiches du lot restent utilisables. |
| Relecture | Lot interrompu (fermeture du navigateur, coupure) | Au retour sur `/lots/{id}`, l'état et les corrections déjà enregistrées sur disque sont restitués tels quels ; aucune perte au-delà de la dernière frappe non enregistrée. |
| Relecture | Fiche validée puis modifiée | Statut repasse « à valider » dès la première modification enregistrée ; aucune confirmation n'est demandée pour ce repassage, seulement pour le changement de candidat. |
| Résultat incident | Vide (aucune détection) | Message « Aucune détection sur ce dépôt » ; téléchargement du rapport reste possible (rapport vide valide). |

## Interaction Primitives

- **Enregistrement automatique avec anti-rebond** : chaque champ de la fiche s'enregistre
  ~800 ms après la dernière frappe (pas à chaque caractère), sur disque dans `var/sorties/<id>/`,
  pour permettre la reprise d'un lot interrompu.
- **Raccourcis clavier** (relecture) : `Ctrl+Entrée` valide la fiche courante ; `Ctrl+Alt+↓` /
  `Ctrl+Alt+↑` (boutons « Suivante »/« Précédente » toujours visibles en parallèle) passent à la
  fiche suivante / précédente du tiroir ; `Échap` ferme toute boîte de confirmation ouverte.
  `Alt+↓`/`Alt+↑` sont évités : ils entrent en conflit avec l'ouverture native d'une liste
  déroulante Windows quand le focus est sur un `<select>`. Tout raccourci de navigation de fiche
  est inactif tant que le focus se trouve dans un champ de formulaire (texte, zone de texte,
  liste déroulante), pour ne pas interrompre la saisie.
- Le clic est toujours disponible en parallèle du clavier ; aucun raccourci n'est la seule façon
  d'accomplir une action.

## Accessibility Floor

Comportemental ; le contraste visuel est dans `DESIGN.md`.

- Contraste WCAG 2.1 AA sur toutes les combinaisons de texte porteuses de sens (ratios dans
  `DESIGN.md.Colors`).
- Tout accessible au clavier (tabulation, raccourcis ci-dessus), focus toujours visible via le
  token `focus` de `DESIGN.md` (contour 2px + décalage 2px, jamais le seul changement de couleur
  de bordure).
- Chaque champ a un libellé associé par `for`/`id` (pas de placeholder seul en guise de libellé).
- `aria-live="polite"` sobre, un résumé agrégé par mise à jour plutôt qu'une annonce par ligne :
  l'indicateur d'enregistrement annonce son propre changement d'état (« Enregistré ») ; le
  journal d'événements et la barre de progression n'annoncent que par palier (ex. toutes les 2
  fiches, ou au changement d'état du lot), jamais une annonce par événement reçu. `aria-busy="true"`
  posé sur le panneau de fiche pendant la régénération d'un candidat, avec une annonce ponctuelle
  à la fin.
- `prefers-reduced-motion` respecté : les transitions d'état (apparition de fiche, changement de
  pastille) sont supprimées si demandé par le système.
- Attribut `lang` posé sur les zones de contenu dans la langue choisie pour le lot (`fr` ou
  `en`) — panneau note et formulaire de fiche — distinct du `lang="fr"` de l'interface elle-même.

## Responsive & Platform

Portable 1366 à 1920 px de large uniquement ; pas de mobile, pas de redimensionnement en deçà de
1366 px (le tiroir se replie en premier pour libérer de la place, puis la mise en page ne descend
pas plus bas). Windows 11, sans droits administrateur. Servie sur `127.0.0.1` (ou `[::1]`), aucun
accès réseau sortant à l'exécution. Navigateurs cibles : Edge et Chrome récents.

## Inspiration & Anti-patterns

- **Rejeté — tableau de bord animé ou vitrine** : WaveAudit est un outil de relecture, pas une
  démo commerciale ; aucune animation qui ne serve pas la compréhension d'un changement d'état.
- **Rejeté — édition des récits d'incident en v2** : le workflow incident reste lecture +
  téléchargement ; pas de formulaire de correction côté CERT pour cette version.
- **Repris du contrat existant** : la structure deux-colonnes de la relecture (note à gauche,
  fiche à droite) et le tiroir repliable sont des décisions déjà verrouillées (memlog), pas des
  inventions de cette spine.

## Key Flows

### Flow 1 — Camille, consultante pentest (rendu du rapport le lendemain)

1. Camille ouvre WaveAudit sur son poste. Elle choisit le workflow « Fiches » et dépose ses 12
   notes de mission (glisser-déposer sur la carte de dépôt).
2. Elle choisit le modèle par défaut (durée indicative affichée : ~20 s/fiche) et la langue
   « Français », puis lance le lot.
3. Elle suit la barre de progression et le journal pendant que les fiches se génèrent ; elle
   ouvre la relecture dès que la première fiche est prête, sans attendre la fin du lot.
4. Pour chaque fiche, elle relit le texte généré à côté de sa note source (panneau de gauche).
   Sur la note « 01 — XSS réfléchi », le candidat proposé par défaut ne correspond pas : elle
   clique l'onglet du candidat « WEB-XSS-REFLECHI » dans la barre des candidats ; la fiche se
   régénère sur ce constat (quelques secondes, mention « Génération en cours »).
5. Elle corrige la description et le champ CVSS de la nouvelle fiche ; l'indicateur passe à
   « Enregistré » quelques instants après sa dernière frappe.
6. Elle valide la fiche (`Ctrl+Entrée`), passe à la suivante (`Ctrl+Alt+↓` ou bouton
   « Suivante »), et répète jusqu'à la douzième note.
7. **Climax** : une fois les 12 fiches validées, elle clique « Exporter ». Le téléchargement du
   rapport Word démarre immédiatement ; elle l'ouvre pour vérifier la table de synthèse avant de
   l'envoyer au client, le lendemain matin comme prévu.

Échec : si le moteur devient injoignable en cours de lot, le journal affiche l'erreur, les fiches
déjà terminées restent utilisables en relecture ; Camille peut relancer plus tard en reprenant le
même lot depuis « Lots récents ».

Chemin alternatif — brouillon : à 17h, avec seulement 9 des 12 fiches validées, Camille doit
partir ; elle clique « Exporter un brouillon ». Le rapport Word se télécharge immédiatement,
toutes les fiches incluses, les 3 non validées marquées « non validée » dans le document ; elle
reprendra la relecture le lendemain matin depuis « Lots récents » avant l'export final.

### Flow 2 — Karim, analyste CERT (journaux d'un bastion compromis)

1. Karim ouvre WaveAudit, choisit le workflow « Incident » et dépose le dossier exporté du
   bastion (journaux Windows en `.json`, `.log` Linux).
2. Il lance l'analyse et suit la barre de progression ; pas de choix de modèle ni de langue pour
   ce workflow (règles de détection, pas de génération par modèle).
3. Une fois terminé, il arrive sur le résumé des détections, groupées par sévérité. Il clique la
   carte « Critique » : la liste se filtre sur les détections correspondantes (ex. « Accès
   LSASS »).
4. Il lit chaque détection (titre, description, références MITRE ATT&CK, occurrences).
5. **Climax** : il clique « Télécharger le rapport ». Le fichier `.docx` se télécharge
   immédiatement ; il le joint à sa main courante d'incident sans étape intermédiaire.

Échec : si le dossier déposé ne contient aucun fichier reconnu, le résumé affiche « Aucune
détection sur ce dépôt » plutôt qu'une erreur — le dépôt a été lu, simplement rien n'y correspond
aux règles.

## Questions ouvertes

Ce que les décisions (memlog) ne tranchent pas ; à trancher par l'architecture ou en continuant
le cadrage, pas par cette spine :

- **Contrat d'API du workflow incident** : routes exactes (`/incidents` ou extension de `/lots`
  avec un `workflow` distinct), format de `GET /incidents/{id}/etat`. Cette spine suppose des
  routes symétriques à `/lots` mais ne les verrouille pas.
- **Enregistrement des corrections** : forme exacte de l'écriture incrémentale (un PATCH par
  champ ? tout le corps de la fiche à chaque anti-rebond ?) — non spécifiée dans contrats.md
  aujourd'hui.
- **Relance d'une fiche sur un autre candidat** : endpoint dédié ou nouvel appel complet de
  génération pour cette seule fiche ; impact sur la numérotation des événements du journal.
- **Liste des modèles proposée à l'UI** : contrats.md ne décrit pas encore l'endpoint qui expose
  le manifeste des modèles installés avec durée et mémoire indicatives.
- **Export brouillon** : format exact de la mention « non validée » dans le corps du document
  Word (ligne ajoutée, filigrane, les deux ?) — à confirmer avec contrats §18 (export).
- **Persistance de l'état du tiroir** (ouvert/replié) entre deux ouvertures de la même page : pas
  demandée explicitement, laissée en confort local (voie rapide) plutôt que verrouillée ici.

Tranché par cette relecture (plus une question ouverte) : l'encart des motifs reste affiché
pendant toute la correction d'une fiche « à revoir », chaque motif marqué « signalé à la
génération » ; il ne disparaît jamais automatiquement, seulement à la validation de la fiche (voir
Component Patterns, Encart des motifs).
