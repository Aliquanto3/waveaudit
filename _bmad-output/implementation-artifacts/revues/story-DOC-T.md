# Revue — story DOC-T (guide des testeurs pour collègues auditeurs)

Commit relu : 0a0dc08 (base 1d354e6), branche `doc-testeurs`. Documentation seule
(`docs/guide-testeurs.md`, `README.md`, modèle d'issue). Verdict : structure et public visés
atteints ; quatre inexactitudes moyennes (réseau d'entreprise, PATH, repli de modèle) et
plusieurs faibles, toutes corrigées dans le guide.

| Sévérité | Source | Constat | Décision |
|---|---|---|---|
| moyenne | second avis 1 | Inspection TLS : `UV_NATIVE_TLS` ne vaut que pour uv ; `waveaudit installer` (httpx, `trust_env=True`) utilise certifi sauf `SSL_CERT_FILE`/`SSL_CERT_DIR`. | Corrigé : `SSL_CERT_FILE` vers le certificat racine PEM fourni par le support, valable pour les deux commandes (vérifié dans `httpx._config.create_ssl_context`, httpx 0.28.1). |
| moyenne | second avis 2 | Domaines incomplets (PyPI, redirections CDN, `follow_redirects=True`). | Corrigé : `pypi.org`, `files.pythonhosted.org`, `github.com`, `huggingface.co`, et mention des redirections vers leurs serveurs de diffusion. |
| moyenne | second avis 3 | `uv` absent du PATH du terminal ouvert avant son installation. | Corrigé : ouvrir un nouveau terminal, contrôle `uv --version`. |
| moyenne | second avis 4 | « l'interface vous l'indique » faux : aucun message n'annonce le repli. | Corrigé : le seul signe est le modèle présélectionné à l'accueil (`modeles_installes` appelle `choisir_modele`, RAM mesurée au rendu de la page) ; noms des modèles cités ; demander le modèle utilisé dans le retour. La fiche de story disait aussi « annoncé à l'accueil » : corrigée. |
| faible | second avis 5 | README « version candidate 0.2.0 » vs pyproject 0.1.0. | Formulation gardée (0.2.0rc1 posée après fusion) ; le guide indique `waveaudit 0.2.0rc1` ou plus récent. pyproject non touché. |
| faible | second avis 6 | `Ctrl+Alt+↓/↑` inactifs quand le focus est dans un champ (`relecture.js`, `focusDansChamp`). | Corrigé : précisé, avec la sortie (cliquer hors des champs, ou boutons « Suivante »/« Précédente »). `Ctrl+Entrée` marche partout (vérifié). |
| faible | reviewer | « par glisser-déposer » : aucun gestionnaire de dépôt dans l'UI (`dragover`/`drop` absents). | Corrigé : sélecteur de fichiers (`Ctrl`+clic), puis « Lancer le lot ». |
| faible | reviewer | « `catalogue verifier` contrôle que le catalogue est en cause » : sens inversé. | Corrigé. |
| faible | reviewer | `exporter <id>` présenté « final ou brouillon » sans l'option. | Corrigé : `--brouillon` cité. Titre d'annexe aligné sur le rapport (« Annexe — notes écartées »). |
| faible | reviewer | `HTTPS_PROXY` posé par `$env:` ne vaut que pour le terminal courant ; « console » ambigu pour un usage par l'interface. | Corrigé. |
| — | reviewer | Complexité : 0 constat (documentation seule). | — |

Vérifié conforme : libellés de l'UI cités (« Exporter un brouillon », « Télécharger le rapport »,
« Suivante », « Enregistrement… », « Enregistré », « Génération en cours », workflow « Fiches »
présélectionné), port 8765, commandes `version`, `catalogue verifier`, `exporter`, notes de
démonstration citées, tailles et URL de `config/artefacts.toml`, seuil `ram_min_defaut_go = 4.5`.

## Points pour Anaël

- Créer le label `retour-testeur` (orchestrateur).
- Poser la version 0.2.0rc1 après fusion (le guide l'annonce).
- Non vérifiable ici : installation réelle derrière le proxy d'entreprise avec inspection TLS
  (`SSL_CERT_FILE` + `UV_NATIVE_TLS`) ; à faire par un premier testeur sur un PC Wavestone.
