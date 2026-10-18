# Revue — story W4 (workflow incident dans l'UI)

Commit relu : 3e50de9 (base 67ed56a), branche `worktree-agent-a1f3a91735a27bb52`. X2 et LIB en
parallèle (`application/export.py`, `cli.py`, `adaptateurs/export_docx.py`) : non touchés ;
`composition.py` : rien de plus que l'ajout du dev.
Verdict : routeur conforme à §26 (ordre de lancement A1/A2, refus après l'id, 409 avec
`occupation`, `dossier_lot_existant` partout, 303 `/incidents/{id}` → `/lots/{id}`), §30 et
§11 ; le défaut haut (incident inatteignable depuis l'accueil) et un défaut moyen corrigés.

| Sévérité | Source | Constat | Décision |
|---|---|---|---|
| haute | second avis 1 | L'accueil n'a ni choix fiches / incident (EXPERIENCE « Accueil », prototype `.choix-workflow`) ni formulaire vers `POST /incidents` : CAP-14 « Depuis l'accueil » non tenu, seul un envoi forgé avec le jeton y mène. Reporté par le dev (fichiers hors liste). | Corrigé (décision de l'orchestrateur, sans toucher `pages.py` ni `app.py`) : `index.html` gagne un groupe `role="group"` « Choix du workflow » à deux boutons `aria-pressed`/`aria-controls` et un formulaire `#depot-incident` (`journaux` multiple, `modele` avec le défaut présélectionné, `annee` 1970–2100 vide = année courante, pas de langue), désactivé comme le dépôt fiches si un lot tourne. `accueil.js` bascule les formulaires et envoie l'un ou l'autre par `WaveAudit.envoyer` (jeton CSRF, 303 suivi, message codé sur refus). `style.css` : `.choix-workflow`, `.carte-workflow`, et `[hidden] { display: none !important }` (sans elle, `form { display: flex }` affichait le formulaire caché). Tests `e2e::test_accueil_formulaire_incident_aboutit_au_suivi` (action, noms des champs et jeton lus dans `GET /`, 403 sans jeton, 303 puis suivi 200 et 16 détections) et `test_accueil_lot_en_cours_desactive_aussi_le_depot_incident`. `test_accessibilite_accueil` et `test_pages_portent_le_jeton_sans_script_ni_style_en_ligne` couvrent le nouvel HTML sans changement. |
| faible | second avis 2 | `journal_reconnu` importe `router_journal` localement alors que le module importe déjà `adaptateurs.journaux`. | Rejeté : choix motivé dans la spec (ajout en fin de fichier seulement, X2 croise le bloc d'imports) ; sans effet sur `test_architecture.py`. Regroupable après la fusion de X2. |
| faible | second avis 3 | `afficherResultat` (`incident.js`) : un 409/404 de `/resultat` donnait une section vide et un lien `.docx` vers une erreur. | Corrigé : réponse non `ok` → message codé (`WaveAudit.messageErreur`) dans `#etat-texte`, section laissée cachée ; erreur réseau signalée. |
| faible | second avis 4 | `GET /incidents/{id}/etat` renvoie aussi l'état d'un lot de fiches. | Rejeté : §26 « forme de `/lots/{id}/etat` », la réponse porte `workflow`, `/lots/{id}/etat` ne contrôle pas non plus le workflow (symétrie W2) ; la page `/incidents/{id}` redirige déjà un lot de fiches. |
| moyenne | reviewer | `_resoudre_annee` : `"--5".lstrip("-").isdigit()` est vrai puis `int("--5")` lève ; 5 000 chiffres dépassent la limite de conversion d'`int` (3.12) : réponse `500 erreur_interne` au lieu de `422 annee_invalide`. | Corrigé : motif `-?[0-9]{1,6}` avant `int()`. `e2e::test_annee_invalide` étendu (`--5`, 5 000 chiffres, chiffres arabes). |
| — | reviewer | Complexité : 0 constat nouveau. `incident.js` ajoute les événements par `depuis` (incrémental) ; le tableau est reconstruit au clic d'un filtre (borné par les détections). `GET /incidents/{id}/etat` relit le journal à chaque sondage : hérité de §30, laissé comme en W2 (journal incident de quelques lignes). | — |

Vérifié conforme : ordre de lancement §26 (occupation provisoire, validation des journaux puis
modèle et année, `nouvel_id_lot`, `definir`, écriture, `lot.json` avant le 303, `fermer` en
`run_in_threadpool`, fil daemon, `liberer` en `finally`) ; `aucun_journal_reconnu` sans dossier
créé ; noms assainis (`Path.name`, motif, réservés Windows, doublons casefold) ; tailles
bornées (50 fichiers, 10 Mio, 50 Mio au middleware) ; modèle `externe` passé `None` ; aucun
GET n'écrit ; CSP sans script ni style en ligne ; contenu du `.docx` égal à celui de la CLI
(oracle indépendant : chemin CLI distinct sur le même dépôt). `router_journal` : aucun autre
appelant de `_router` (`git grep`).

Tests : `e2e/test_incident_ui.py` 12 verts ; `tests/e2e` 143 verts ; suite complète 1005 verts ;
ruff check et format propres.

## Interfaces et consignes pour la suite

- **W3b (relecture)** : `style.css` porte maintenant, en fin de fichier, les blocs W4
  « Page incident » (`#resume`, `#detections`) et « Accueil » (`[hidden]`, `.choix-workflow`,
  `.carte-workflow`) : ajouter à la suite sans les réécrire. `[hidden] { display: none
  !important }` vaut pour toute la page : un tiroir ou un onglet masqué par `hidden` le reste
  même si sa règle pose `display` ; pour un panneau animé, basculer une classe plutôt que
  `hidden`. Accueil : deux formulaires `form.depot[data-workflow]` (`#depot` → `/lots`,
  `#depot-incident` → `/incidents`) et un seul `#depot-message` ; `accueil.js` traite tout
  `form.depot` — un nouveau formulaire de dépôt n'a qu'à porter cette classe. Les ids
  `modele` (fiches) et `modele-incident` sont distincts.
- **REC** : vérifier dans un vrai navigateur la bascule fiches / incident (formulaire caché
  non affiché), l'envoi d'un dépôt incident et le message `aucun_journal_reconnu` sur
  l'accueil (aucun test n'exécute le JS).
