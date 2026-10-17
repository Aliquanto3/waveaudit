# Revue — story 8 « Installation vérifiée et SBOM »

Branche `story-8-revue` (depuis `story-8`, 2662c4f, déjà à jour sur `main` c1ab8ff, sans conflit). Contrat : contrats §11, AD-12, stories.yaml id 8.

## Revue

| Sévérité | Source | Constat | Décision | Motif |
|---|---|---|---|---|
| high | second avis 1 | `httpx.Client` sans `follow_redirects=True` : GitHub releases et Hugging Face `resolve` répondent 302, `raise_for_status` levait, aucune installation réelle possible | corrigé | `follow_redirects=True` ; test `test_redirection_suivie` (302 vers un CDN, échoue sur le code d'origine) |
| medium | second avis 2 | Renommage du `.part` avant la vérification, contraire à §11 (« vérifie la taille puis le SHA-256, puis renomme ») | corrigé | `_telecharger_verifie` vérifie le `.part` (taille puis SHA-256) puis renomme ; test `test_mauvaise_empreinte_ne_laisse_ni_final_ni_part` |
| low | second avis 3 | `timeout=None` : une connexion figée bloque indéfiniment | corrigé | `httpx.Timeout(60.0)` par opération (connexion, lecture d'un bloc), pas sur le transfert entier |
| low | second avis 4 | Zip slip non contrôlé | rejeté | `zipfile.extractall` (3.12) neutralise `../` et les chemins absolus (vérifié : extraits sous la destination) ; l'archive est en outre vérifiée par SHA-256 avant extraction |
| low | second avis 4 | Ré-extraction à chaque appel ; `chemin()` ne vérifie pas l'existence de l'exécutable | reporté | inoffensif (zip de 20 Mo) ; l'existence de `llama-server.exe` dans le zip est à confirmer à la première installation réelle (§11 : « à confirmer en ouvrant le zip ») |
| low | second avis 5 | Schéma https non imposé | rejeté | manifeste versionné et testé (URL épinglées) ; l'intégrité repose sur le SHA-256, pas sur le transport |
| low | second avis 6 | `.part` non nettoyé si le flux échoue | corrigé | suppression du `.part` sur toute exception ; test `test_erreur_http_ne_laisse_pas_de_part` |
| low | revue | Une erreur HTTP ou réseau remonte en `httpx.HTTPError`, hors hiérarchie `ErreurWaveAudit` : la commande `installer` sortirait en trace brute | reporté | contrat muet (§4 ne mappe que `EmpreinteInvalide` → 5) ; à traiter par la story CLI (message clair, code non nul) sans élargir le contrat en silence |

Complexité : 0 constat (lecture et hachage en flux par blocs de 1 Mo, aucune structure qui grossit).
Intégration : `installer(manifeste, var, candidats, transport=None)` exposée ; pas encore d'appelant (`interfaces/cli.py` : story ultérieure). `cyclonedx-bom` déclaré dans les dépendances.
Report (service réel) : première installation sur le poste cible — vérifier les redirections réelles derrière le proxy d'entreprise (`trust_env=True`), les tailles et SHA-256 du manifeste, et le chemin `llama-server.exe` dans le zip b11714.
Tests : ciblés 28 verts (installation + architecture) ; suite complète 185 verts ; ruff check et format verts.
