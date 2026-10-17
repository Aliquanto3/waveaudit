# Formats : note, constat type, fiche

Contrat de données du POC. Les noms de champs sont normatifs ; leur encodage (YAML, modèles Python) relève de l'architecture.

## Note brute (entrée, CAP-1)

Un fichier `.md` ou `.txt` par constat, en UTF-8.

| Champ | Obligatoire | Contenu |
|---|---|---|
| `titre` | non | Intitulé libre donné par le consultant |
| `actif` | non | Cible (URL, hôte, application) |
| `severite_pressentie` | non | `critique` / `elevee` / `moyenne` / `faible` / `info` |
| `constat_attendu` | non | Identifiant de constat type. Présent seulement dans les notes de démonstration, pour mesurer CAP-3 ; ignoré par le traitement |
| corps | oui | Texte libre : observations, preuves (requêtes, sorties d'outils) |

Les champs sont dans un en-tête YAML optionnel (`---` … `---`). Une note dont le corps est vide est invalide.

## Constat type (catalogue, CAP-2)

| Champ | Contenu |
|---|---|
| `id` | Identifiant stable, par exemple `WEB-XSS-REFLECHI` |
| `titre` | Intitulé FR |
| `famille` | `web` / `ad` / `infra` / `config` / `crypto` / `autre` |
| `mots_cles` | Termes FR et EN qui servent à la recherche |
| `description` | Texte générique FR |
| `impact` | Texte générique FR |
| `recommandation` | Texte générique FR |
| `cvss_vecteur` | Vecteur CVSS 3.1 par défaut (`CVSS:3.1/AV:…`) |
| `references` | Liste de `{id, titre, url}` : CWE-n, WSTG-…, guide ANSSI |
| `source` | Origine et licence du contenu |

Couverture minimale : web (OWASP Top 10 et WSTG courants), Active Directory, infrastructure et configuration, cryptographie, au moins 30 entrées.

## Fiche (sortie, CAP-4 à CAP-6)

| Rubrique | Règle |
|---|---|
| Titre | Celui du constat type, adaptable |
| Description | Adaptée aux notes (actif, preuves) |
| Impact | Adapté au contexte |
| Recommandation | Adaptée, actionnable |
| CVSS 3.1 | Vecteur validé et score calculé par le code, avec la sévérité qui en découle |
| Références | Sous-ensemble des références du constat type retenu, rien d'autre |
| Statut | `ok` ou `a_revoir` (repli, ou référence ou vecteur corrigé), avec le motif |
| Traçabilité | Fichier de note source et identifiant du constat type |

Le rapport Word porte en tête et en pied le bandeau « Démonstration — données fictives ».
