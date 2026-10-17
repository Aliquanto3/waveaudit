# État de nuit

| Story | Titre | État |
|---|---|---|
| 1 | Socle commun | intégrée 080d53e (revue : revues/story-1.md, validée par Anaël) |
| 2 | Recherche BM25 | intégrée b74abe1 (revue : revues/story-2.md) |
| 3 | CVSS 3.1 et garde-fous | intégrée c980c3f (revue : revues/story-3.md) |
| 4 | Catalogue de constats types | intégrée 2fef712 (revue : revues/story-4.md ; suite 106 verte) |
| 5 | Notes brutes et jeu de démonstration | intégrée 2162444 (revue : revues/story-5.md ; suite 165 verte) |
| 6 | Adaptateur moteur OpenAI | intégrée 2277976 (revue : revues/story-6.md) |
| 7 | Garde réseau | intégrée 8be7a3e (revue : section « Revue » de stories/story-7-garde-reseau.md) |
| 8 | Installation vérifiée et SBOM | intégrée 7769749 (revue : revues/story-8.md) |
| 9 | Export Word et thèmes | intégrée 28b7a07 (revue : revues/story-9.md ; suite complète de vague C : 196 verte, lint OK) |
| 10 | Pipeline fiches et prompt | intégrée 50e52b1 (revue : revues/story-10.md) |
| 11 | Calibrage du rattachement | intégrée 9493e69 (revue : revues/story-11.md ; CAP-3 démo : 17/20 top 1, 20/20 top 3 ; suite 212 verte) |
| 12 | Composition, lot, llama-server | intégrée f31117e (revue : revues/story-12.md ; suite complète de vague E : 238 verte, lint OK) |
| 13 | CLI complète | intégrée 5f3a388 (revue : revues/story-13.md ; suite 271 verte) |
| 14 | UI web locale | intégrée 41b03c8 (revue : revues/story-14.md) |
| 15 | Banc de mesure | intégrée b8022b2 (revue : revues/story-15.md) |
| 16 | Preuve hors ligne, test réel, README | intégrée 612457c (revue : revues/story-16.md ; suite complète de fin de MVP : 283 verte, lint OK) |
| V1 | Validation sur le vrai moteur | à faire |
| V2 | Banc des 4 modèles et réglage du prompt | à faire |
| D1 | Catalogue élargi et notes difficiles | intégrée 1d4f448 (revue : revues/story-D1.md ; 50 constats ; notes 21-30 : 8/10 top 1, 10/10 top 3) |
| D2 | Intégration continue GitHub Actions | intégrée 79abdfd (revue : revues/story-D2.md ; badge README fait par la story 16 ; premier run CI 39070885639 vert sur windows-latest) |
| D3 | Guide des testeurs et formulaire de retour | intégrée e93367d (revue : revues/story-D3.md ; suite complète de vague L : 283 verte ; durées du guide estimées, installer non exécuté) |
| C1 | Extension du socle pour le CERT | intégrée 5e5c42d (revue : revues/story-C1.md ; V1 reportée par arbitrage ; suite 414 verte) |
| C2 | Lecture des journaux et jeu de démo | en cours |
| C3 | Règles et moteur de détection | en cours |
| C4 | Indicateurs et garde-fous du récit | en cours |
| C5 | Workflow incident, service, calibrage | à faire |
| C6a | Rapport d'incident Word | en cours |
| C6b | CLI incident, hors ligne, README | à faire |

## Arbitrages d'Anaël (2026-10-17, soir)

- Ordre modifié : V1 et V2 passent en tout dernier, après K à P, et seulement si tout le reste est réalisé. C1 démarre donc avec V1 « non faite, reportée ». Le téléchargement de V1 (`installer --candidats`) reste autorisé à ce moment-là.
- Parallélisation autorisée si le risque est très faible : D1 et D2 partent pendant la vague G (D2 sans badge README, ajouté par la story 16) ; 15 et 16 partent ensemble après l'intégration de 13. Le CERT reste séquentiel (C1 exige 1 à 16).

## Écarts à arbitrer

- Story 2 : la tokenisation remplace œ, æ, ß (oe, ae, ss) avant NFKD ; le §7 ne cite que NFKD (sans cela « œuvre » donne « uvre »). Écart mineur, à entériner dans contrats.md.
- Story 3 (reporté par la revue) : conformément au §6, un titre de moins de 20 caractères (ex. « Injection SQL ») est remplacé par celui du constat type et la fiche passe `a_revoir` ; seuil probablement trop strict, à vérifier au banc.
- Story 4 (reporté, réseau requis) : vérifier que les 41 URL du catalogue répondent, et ajouter des références ANSSI vérifiées en ligne (le catalogue n'en cite aucune).
- Story 7 (reporté) : sous Windows, une boucle asyncio Proactor échappe au garde (sockets non Python). Le relecteur a aussi gardé sendto/sendmsg (UDP), que le §12 ne liste pas.
- Story 5 (reporté) : notes de démo en prose, peu de jargon ; BM25 seul classe le bon constat 1er pour 15/20, top 3 pour 19/20 (05-idor raté). À revoir après le premier banc.
- Story 8 (reporté) : première installation réelle à vérifier (proxy, empreintes du manifeste, présence de llama-server.exe dans le zip) ; la CLI devra traduire les erreurs httpx en message clair.
- Story 9 : le §17 ne prévoit pas de thème privé invalide (couleur hors #RRGGBB, TOML mal formé, modele.docx illisible) ; la revue lève `ConfigurationInvalide` (code 2) dès la construction de l’export, plutôt qu’un repli silencieux. Logo du thème privé validé mais pas encore inséré dans le document.
- Story 10 (à arbitrer) : (a) la nouvelle tentative sur SortieInvalide rejoue les mêmes messages, seed 42 et température 0,2 : sur le vrai modèle, elle reproduira sans doute la même sortie ; varier la seed touche le port `Moteur` du socle, donc amender le §5 après le banc. (b) Un `</note>` dans le corps ou l’actif d’une note n’est pas échappé et sort du bloc délimité (forme figée par le §8 ; risque faible, les notes viennent du consultant). (c) Moteur tombé en cours de lot : repli note par note, avec 180 s de délai chacune, sans coupure du lot (conforme au §5, à revoir avec la story 12).
- Story 11 : le score CAP-3 (17/20, 20/20) est mesuré sur le jeu de démo qui a servi au calibrage ; la revue a retiré les mots-clés recopiés des notes (sur-apprentissage). Un jeu de notes de validation non vu manque pour une mesure honnête (D1 peut le fournir).
- Story 12 : `composition.ouvrir(config, modele, *, id_lot=None)` (mot-clé ajouté pour nommer le journal de llama-server) ; `fiches.json` écrit sans écriture atomique (non demandée par le contrat) ; une exception inattendue de `traiter` arrête le lot (code 4, §4).
- Story 14 : l’UI accepte `Host: [::1]:<port>` (écart au §18, nécessaire puisque le §18 autorise `ui.hote = "::1"`) ; `/etat?depuis=N` facultatif ajouté (réponse par défaut inchangée). Reporté : le champ `erreur` d’un lot peut afficher un chemin absolu.
- Story 13 (reporté) : vérifier à la main qu’un second `waveaudit ui` sur un port occupé sort en code 4.
- Story 15 : le §20 ne définit pas `pic_rss_total_o` ; la revue retient le maximum de la somme application + moteur prise au même échantillon (pic simultané). À consigner dans le §20.
- Story 16 (reporté) : le test slow de bout en bout n’a pas été lancé (pas de modèle) ; à lancer en V1.
- Story C1 (à trancher dans le §21) : les motifs normatifs MOTIF_TECHNIQUE, MOTIF_IPV4 et MOTIF_HACHAGE (lookahead `(?![d.])`) ratent un jeton suivi d’un point final, et MOTIF_IPV6 avale ce point. Une technique ou une IP inventée en fin de phrase passerait donc les garde-fous du récit (CAP-5). Motifs inchangés. Décision de nuit (orchestrateur) : C4 applique les motifs sur une copie du texte de même longueur où chaque « . » suivi d’un blanc ou de la fin est remplacé par une espace (traitement proposé par la revue C1), et le consigne. Autre point : `ouvrir_moteur_incident(..., *, id_lot=None)` (mot-clé ajouté, comme `ouvrir`).
- Story 6 : le §3 ne classe pas une enveloppe de réponse 200 non conforme (corps non JSON, `choices` vide, `message` absent) ; la revue lève `MoteurInjoignable` (et `SortieInvalide` seulement pour un `content` null ou non textuel). À entériner.
