# Formats : journaux, règles, détections, rapport d'incident

Contrat de données du workflow CERT. Les formes Python exactes sont dans `contrats.md` §21.

## Entrées (CAP-1)

Un dossier, lu sans descendre dans les sous-dossiers.

| Fichier | Format |
|---|---|
| `*.json` | Tableau d'objets Windows : `TimeCreated` (ISO 8601 avec fuseau), `Id` (int), `LogName`, `ProviderName`, `MachineName`, `Message`, et `Data` (objet des champs EventData : `TargetUserName`, `IpAddress`, `LogonType`, `CommandLine`, `Image`, `Hashes`, `ParentImage`, `ServiceName`, `TaskName`, `GroupName`…) |
| `*.csv` | Mêmes colonnes de tête (`TimeCreated`, `Id`, `LogName`, `ProviderName`, `MachineName`, `Message`) ; toute autre colonne va dans `Data` ; UTF-8 (avec ou sans BOM), séparateur `,` ou `;` détecté |
| `auth.log*`, `syslog*`, `secure*`, `*.log` | Lignes RFC 3164 : `Mmm jj hh:mm:ss hote programme[pid]: message` |

## Règle de détection (CAP-2)

| Champ | Contenu |
|---|---|
| `id` | `INC-WIN-…` ou `INC-LIN-…`, unique |
| `titre`, `description`, `impact`, `recommandation` | Texte type en français |
| `severite` | `critique` / `elevee` / `moyenne` / `faible` |
| `references` | Liste de `{id, titre, url}` : techniques ATT&CK `T1110`, `T1110.001`… (URL attack.mitre.org) |
| `source` | `windows` ou `linux` |
| `condition` | Tous les critères présents doivent être vrais : `event_id` (liste), `log_name`, `programme` (Linux), `champs` (égalité exacte, insensible à la casse), `champs_regex`, `message_regex` |
| `agregation` | Facultatif : `seuil` (int), `fenetre_s` (int), `par` (liste de champs). La détection naît quand au moins `seuil` événements du même groupe tombent dans la fenêtre |

Catalogue minimal (15) :
- Windows : `INC-WIN-FORCE-BRUTE` (4625), `INC-WIN-CONNEXION-RDP` (4624, LogonType 10), `INC-WIN-COMPTE-CREE` (4720), `INC-WIN-AJOUT-GROUPE-ADMIN` (4728, 4732, 4756), `INC-WIN-JOURNAL-EFFACE` (1102, 104), `INC-WIN-SERVICE-INSTALLE` (7045), `INC-WIN-TACHE-PLANIFIEE` (4698), `INC-WIN-POWERSHELL-ENCODE` (Sysmon 1 ou 4688, `-enc`), `INC-WIN-ACCES-LSASS` (Sysmon 10, cible lsass.exe), `INC-WIN-OUTIL-OFFENSIF` (Sysmon 1, nom ou hachage d'outil connu).
- Linux : `INC-LIN-SSH-FORCE-BRUTE`, `INC-LIN-SSH-CONNEXION-ROOT`, `INC-LIN-SUDO-SHELL`, `INC-LIN-COMPTE-CREE` (useradd), `INC-LIN-CLE-SSH-AJOUTEE` (authorized_keys).

## Détection et indicateurs (CAP-3, CAP-4)

- **Détection :** une règle, ses événements déclencheurs (les `max_preuves` premiers sont cités), le début et la fin, les hôtes.
- **Indicateurs :** type parmi `ip`, `compte`, `hote`, `hachage`, `executable`. Chacun porte sa valeur normalisée et ses origines (fichier et ligne).

## Rapport d'incident (CAP-6)

Ordre des sections :

1. Bandeau « Démonstration — données fictives »
2. Synthèse : période, nombre de détections par sévérité, hôtes touchés (déterministe)
3. Chronologie : tableau `Horodatage | Hôte | Fait | Sévérité`
4. Faits détectés : par détection, son récit, son impact, la recommandation, les références ATT&CK, les preuves (`fichier:ligne` et extrait), et le statut avec ses motifs
5. Indicateurs de compromission : tableau `Type | Valeur | Origines`
6. Actifs touchés
7. Recommandations consolidées, dédoublonnées
8. Annexe : sources analysées (fichier, lignes lues, lignes ignorées)
