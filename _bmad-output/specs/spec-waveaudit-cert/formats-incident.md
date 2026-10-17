# Formats : journaux, règles, détections, rapport d'incident

Contrat de données du workflow CERT. Les formes Python exactes et les algorithmes sont dans `contrats.md` §21. Ce fichier est **normatif** : C2 (lecture, démo), C3 (règles) et C4 (indicateurs) s'y rencontrent sans se lire ; la fixture `tests/donnees/incident/canoniques.yaml` (C1) en est la traduction testable.

## Entrées (CAP-1)

Un dossier, lu sans descendre dans les sous-dossiers (routage et encodages : §21 « Lecture »).

| Fichier (casse ignorée) | Format |
|---|---|
| `*.json` | Tableau d'objets Windows : `TimeCreated` (ISO 8601 avec fuseau), `Id` (int), `LogName`, `ProviderName`, `MachineName`, `Message`, `Data` (objet des champs EventData) |
| `*.csv` | Colonnes de tête `TimeCreated`, `Id`, `LogName`, `ProviderName`, `MachineName`, `Message` ; toute autre colonne va dans `champs` ; séparateur `,` ou `;` détecté |
| `auth.log*`, `syslog*`, `secure*`, `*.log` | RFC 3164 `Mmm jj hh:mm:ss hote programme[pid]: message` (`[pid]` facultatif), ou ligne commençant par un horodatage ISO 8601 avec fuseau (rsyslog moderne) |
| `*.gz`, `*.zip`, `*.bz2`, `*.xz`, `.yaml`, `.md`, `.gitkeep`, autres | ignorés en silence : ni événement, ni `LigneIgnoree`, ni entrée dans `fichiers` |

Correspondance vers `Evenement` :

| Champ | Windows | Linux |
|---|---|---|
| `source` | `windows` | `linux` |
| `hote` | `MachineName` verbatim (absent ou vide → `LigneIgnoree`) | hôte de la ligne, verbatim |
| `event_id` | `Id` (JSON int ; CSV chiffres → int ; sinon `LigneIgnoree`) | `None` |
| `log_name` | `LogName` ou `None` | `None` |
| `programme` | `None` | nom avant `[pid]` ou `:`, casse conservée |
| `message` | `Message` ou `""` | texte après `programme[pid]:`, `strip()` |
| `champs` | `Data` (JSON) ou colonnes hors tête (CSV), normalisés ci-dessous | extraits par motif (table Linux) |

## Champs normalisés (`Evenement.champs`)

Valeurs `str` uniquement : entier → `str(int)` (`"10"`), booléen → `"true"`/`"false"`, objet ou liste → `json.dumps(v, ensure_ascii=False, sort_keys=True)`. Valeur `null`, `""` ou blanche → clé **absente**. Aucune autre transformation (pas de strip interne, pas de changement de casse). `Data` non objet → `LigneIgnoree`.

**Windows** : toutes les clés sont recopiées ; celles-ci sont les seules utilisables par une règle (`CHAMPS_WINDOWS`, `domaine/incident.py`) et le jeu de démo les respecte :

| Id | LogName | Clés |
|---|---|---|
| 4624, 4625 | Security | TargetUserName, TargetDomainName, IpAddress, IpPort, LogonType, WorkstationName |
| 4720 | Security | TargetUserName (compte créé), SubjectUserName (créateur) |
| 4728, 4732, 4756 | Security | TargetUserName (= nom du groupe), MemberName (DN du membre), SubjectUserName |
| 4698 | Security | TaskName, SubjectUserName |
| 1102 | Security | SubjectUserName |
| 104 | System | SubjectUserName, Channel |
| 7045 | System | ServiceName, ImagePath, AccountName |
| 1 | Microsoft-Windows-Sysmon/Operational | Image, CommandLine, ParentImage, User, Hashes |
| 4688 | Security | NewProcessName, CommandLine, SubjectUserName |
| 10 | Microsoft-Windows-Sysmon/Operational | SourceImage, TargetImage, GrantedAccess, SourceUser |

**Linux** (`CHAMPS_LINUX`) : `re.search` sur `message`, selon `programme` (`PROGRAMMES_LINUX = {sshd, sudo, useradd}` ; autres programmes : `champs = {}`). Premier motif qui correspond, groupes non capturés absents.

| programme | motif | champs |
|---|---|---|
| sshd | `^(?:Failed\|Accepted) \S+ for (?:invalid user )?(?P<utilisateur>\S+) from (?P<ip>\S+) port (?P<port>\d+)` | utilisateur, ip, port |
| sshd | `^Invalid user (?P<utilisateur>\S+) from (?P<ip>\S+)(?: port (?P<port>\d+))?` | utilisateur, ip, port |
| sudo | `^(?P<utilisateur>\S+) : .*?\bCOMMAND=(?P<commande>.+)$` | utilisateur (l'appelant, jamais `USER=`), commande |
| sudo | puis, dans `commande` : `(?P<fichier_cible>/\S*authorized_keys2?)` | fichier_cible |
| useradd | `new user: name=(?P<nouvel_utilisateur>[^,\s]+)` | nouvel_utilisateur |

(`\|` = barre verticale échappée pour le tableau.)

## Règle de détection (CAP-2)

| Champ | Contenu |
|---|---|
| `id` | `^INC-(WIN\|LIN)-[A-Z0-9]+(-[A-Z0-9]+)*$`, unique, préfixe cohérent avec `source` |
| `titre`, `description`, `impact`, `recommandation` | Texte type en français ; aucun jeton ATT&CK, IPv4, IPv6 ni hachage ; `description`, `impact`, `recommandation` ≥ 20 caractères ; `titre` non vide |
| `severite` | `critique` / `elevee` / `moyenne` / `faible` |
| `references` | ≥ 1 `{id, titre, url}` ; `id` `T\d{4}(\.\d{3})?`, URL `https://attack.mitre.org/techniques/T1110/001/` cohérente avec l'id |
| `source` | `windows` ou `linux` |
| `condition` | Critères, tous vrais (sémantique : §21 « Détection ») : `event_id` (liste), `log_name`, `programme`, `champs` (égalité `casefold`), `champs_regex`, `au_moins_un` (au moins une clé vérifie sa regex), `message_regex`. Au moins un critère |
| `agregation` | Facultatif : `seuil` (≥ 2), `fenetre_s` (≥ 1), `par` (liste de clés, `[]` = un seul groupe) |

Fichiers : `donnees/regles/windows.yaml` et `linux.yaml`, chacun une **liste** de règles. Aucune commande `waveaudit regles verifier` n'est prévue.

### Catalogue minimal (15), conditions normatives

C3 recopie ces conditions et agrégations **telles quelles** (regex entre apostrophes en YAML). C2 construit le jeu de démo contre elles. Regex : `re.search`, `re.IGNORECASE`. Références et sévérités : conseillées, ajustables si `verifier_regles` passe. Ids : `IDS_REGLES_MINIMAUX` (`domaine/incident.py`).

```yaml
INC-WIN-FORCE-BRUTE:        # elevee ; T1110, T1110.001
  condition: {log_name: Security, event_id: [4625]}
  agregation: {seuil: 5, fenetre_s: 300, par: [IpAddress]}
INC-WIN-CONNEXION-RDP:      # moyenne ; T1021.001
  condition: {log_name: Security, event_id: [4624], champs: {LogonType: '10'}}
INC-WIN-COMPTE-CREE:        # moyenne ; T1136.001
  condition: {log_name: Security, event_id: [4720]}
INC-WIN-AJOUT-GROUPE-ADMIN: # elevee ; T1098
  condition:
    log_name: Security
    event_id: [4728, 4732, 4756]
    champs_regex: {TargetUserName: '^(?:administrateurs|administrators|admins du domaine|domain admins|administrateurs de l.entreprise|enterprise admins)$'}
INC-WIN-JOURNAL-EFFACE:     # critique ; T1070.001
  condition: {event_id: [1102, 104]}
INC-WIN-SERVICE-INSTALLE:   # moyenne ; T1543.003
  condition: {log_name: System, event_id: [7045]}
INC-WIN-TACHE-PLANIFIEE:    # moyenne ; T1053.005
  condition: {log_name: Security, event_id: [4698]}
INC-WIN-POWERSHELL-ENCODE:  # elevee ; T1059.001, T1027
  condition:
    event_id: [1, 4688]
    champs_regex: {CommandLine: '(?:^|\s)[-/]e(?:c|nc|ncodedcommand)?\s+[a-z0-9+/=]{16,}'}
INC-WIN-ACCES-LSASS:        # critique ; T1003.001
  condition:
    log_name: Microsoft-Windows-Sysmon/Operational
    event_id: [10]
    champs_regex: {TargetImage: '\\lsass\.exe$'}
INC-WIN-OUTIL-OFFENSIF:     # critique ; T1588.002
  condition:
    log_name: Microsoft-Windows-Sysmon/Operational
    event_id: [1]
    au_moins_un:
      Image: '\\(?:mimikatz|rubeus|sharphound|lazagne)\.exe$'
      Hashes: 'SHA256=A1B2C3D4A1B2C3D4A1B2C3D4A1B2C3D4A1B2C3D4A1B2C3D4A1B2C3D4A1B2C3D4'
INC-LIN-SSH-FORCE-BRUTE:    # elevee ; T1110.001
  condition: {programme: sshd, message_regex: '^Failed password for '}
  agregation: {seuil: 5, fenetre_s: 300, par: [ip]}
INC-LIN-SSH-CONNEXION-ROOT: # elevee ; T1078.003, T1021.004
  condition: {programme: sshd, message_regex: '^Accepted \S+ for root from '}
INC-LIN-SUDO-SHELL:         # elevee ; T1548.003
  condition:
    programme: sudo
    champs_regex: {commande: '^(?:/usr)?/bin/(?:(?:ba|z|da|k)?sh|su)(?:\s|$)'}
INC-LIN-COMPTE-CREE:        # moyenne ; T1136.001
  condition: {programme: useradd, message_regex: '^new user: '}
INC-LIN-CLE-SSH-AJOUTEE:    # elevee ; T1098.004
  condition: {programme: sudo, champs_regex: {commande: 'authorized_keys'}}
```

### Valeurs réservées (fictives)

| Valeur | Usage | Interdit ailleurs |
|---|---|---|
| SHA256 `A1B2C3D4` × 8 (64), MD5 `A1B2C3D4` × 4 (32) | outil offensif de la démo | oui |
| `203.0.113.254`, `"0f" * 32`, `T9999`, `T1110.999` | injectés par le faux moteur (`references_inventees`) | interdits dans le jeu de démo et les textes types |

## Détection et indicateurs (CAP-3, CAP-4)

- **Détection** : une règle, tous ses événements déclencheurs, début, fin, hôtes (algorithme : §21). `indicateurs = []` en sortie de `detecter`, rempli par le pipeline (C5).
- **Indicateurs** : type parmi `ip`, `compte`, `hote`, `hachage`, `executable` ; valeur normalisée ; origines `fichier:ligne`.

| Type | Sources | Normalisation |
|---|---|---|
| ip | `IpAddress`, `ip`, IPv4 de `message` | `ipaddress` ; IPv4 mappée → IPv4 ; exclues : invalides, `0.0.0.0`, `127.0.0.0/8`, `::1`, `::` |
| compte | `TargetUserName` (sauf event_id 4728/4732/4756), `SubjectUserName`, `utilisateur`, `nouvel_utilisateur` | casse conservée, doublons en `casefold` (première graphie) ; exclus : vide, `-`, `SYSTEM`, `LOCAL SERVICE`, `NETWORK SERVICE`, `ANONYMOUS LOGON`, finissant par `$` |
| executable | `Image`, `SourceImage`, `ImagePath` | minuscules, chemin tel quel |
| hachage | `Hashes` (`ALGO=valeur` séparés par `,`) | MD5 (32), SHA1 (40), SHA256 (64 hex) seulement, valeur seule en minuscules ; IMPHASH ignoré |
| hote | `Evenement.hote` | minuscules |

## Jeu de démonstration et oracle (CAP-3, CAP-4)

Dossier lu `donnees/demo/incident/` : `security.json`, `system.json`, `sysmon.csv`, `auth.log`, `syslog`. Oracle **hors du dossier lu** : `donnees/demo/incident-attendu.yaml` (UTF-8, horodatages en chaînes ISO 8601 avec fuseau, entre guillemets).

```yaml
annee: 2026                       # passée en RequeteIncident.annee
decalage_syslog: "+02:00"         # égal à config.incident.decalage_syslog
min_part_benigne: 0.60
detections:                       # dans l'ordre de detecter
  - regle_id: INC-LIN-SSH-FORCE-BRUTE
    debut: "2026-10-14T08:02:10+02:00"
    fin: "2026-10-14T08:03:20+02:00"
    hotes: [BASTION01]            # égalité exacte avec Detection.hotes
    nb_evenements: 8
indicateurs:                      # liste exacte, triée (type, valeur), valeurs normalisées, origines comprises
  - {type: ip, valeur: 203.0.113.45, origines: ["auth.log:12", "auth.log:14"]}
ignorees:                         # lignes volontairement illisibles
  - {fichier: auth.log, ligne: 57}
```

| Règle | Contenu |
|---|---|
| Comparaison (C5) | `debut`/`fin` par égalité d'instants (`datetime.fromisoformat`), le reste par égalité exacte ; liste produite projetée sur ces champs **égale** à la liste attendue ; indicateurs (type, valeur, origines) égaux ; `ignorees` égal |
| Part bénigne | événements lus hors de toute détection / événements lus ≥ `min_part_benigne` ; au moins 80 événements lus |
| Calcul | C2 calcule l'oracle **à la main** (algorithme d'agrégation et règles d'indicateurs de §21, messages compris : une IP dans un `Message` compte) |
| Interdit | régénérer l'oracle, même en partie, depuis une sortie de `executer_incident`, `detecter` ou `extraire` (script, copier-coller) |
| Modification (C5) | seulement là où l'oracle contredit ce fichier ou §21, motif cité dans le commit ; une détection attendue n'est retirée que si la ligne de démo est corrigée |
| Lignes illisibles | au moins une dans `auth.log` et un objet sans fuseau dans `security.json`, hors des lignes d'attaque |

### Chronologie d'attaque normative (2026-10-14, `+02:00`)

C2 reprend ces lignes (forme brute : entrées de `canoniques.yaml`) et les entoure de bénin, sans les modifier. Hôtes en nom court, jamais en FQDN.

| Heure | Fichier, hôte | Ligne d'attaque | Détection |
|---|---|---|---|
| 08:02:10 → 08:03:20 | auth.log, BASTION01 | 8 × `sshd[811]: Failed password for invalid user admin from 203.0.113.45 port 41001…41008 ssh2`, toutes les 10 s | INC-LIN-SSH-FORCE-BRUTE (8 év.) |
| 08:03:41 | auth.log, BASTION01 | `sshd[812]: Accepted password for deploy from 203.0.113.45 port 41022 ssh2` | aucune |
| 08:05:02 | auth.log, BASTION01 | `sudo:   deploy : TTY=pts/0 ; PWD=/home/deploy ; USER=root ; COMMAND=/bin/bash` | INC-LIN-SUDO-SHELL |
| 08:07:15 | auth.log, BASTION01 | `useradd[2311]: new user: name=maintenance, UID=1002, GID=1002, home=/home/maintenance, shell=/bin/bash` | INC-LIN-COMPTE-CREE |
| 08:09:40 | auth.log, BASTION01 | `sudo:   deploy : TTY=pts/0 ; PWD=/home/deploy ; USER=root ; COMMAND=/usr/bin/tee -a /root/.ssh/authorized_keys` | INC-LIN-CLE-SSH-AJOUTEE |
| 08:12:03 | auth.log, BASTION01 | `sshd[2402]: Accepted publickey for root from 203.0.113.45 port 41100 ssh2` | INC-LIN-SSH-CONNEXION-ROOT |
| 09:14:00 → 09:15:15 | security.json, SRV-FICHIERS | 6 × 4625, TargetUserName `administrateur`, IpAddress `192.0.2.10`, LogonType 10, toutes les 15 s | INC-WIN-FORCE-BRUTE (6 év.) |
| 09:15:40 | security.json, SRV-FICHIERS | 4624, LogonType 10, TargetUserName `administrateur`, IpAddress `192.0.2.10` | INC-WIN-CONNEXION-RDP |
| 09:20:11 | security.json, SRV-FICHIERS | 4720, TargetUserName `svc-maj`, SubjectUserName `administrateur` | INC-WIN-COMPTE-CREE |
| 09:20:45 | security.json, SRV-FICHIERS | 4732, TargetUserName `Administrateurs`, MemberName `CN=svc-maj,CN=Users,DC=corp,DC=exemple,DC=test`, SubjectUserName `administrateur` | INC-WIN-AJOUT-GROUPE-ADMIN |
| 09:23:10 | system.json, SRV-FICHIERS | 7045, ServiceName `MajCorp`, ImagePath `C:\ProgramData\maj\maj.exe`, AccountName `LocalSystem` | INC-WIN-SERVICE-INSTALLE |
| 09:24:30 | security.json, SRV-FICHIERS | 4698, TaskName `\MiseAJourCorp`, SubjectUserName `administrateur` | INC-WIN-TACHE-PLANIFIEE |
| 09:41:02 | sysmon.csv, PC-COMPTA07 | Sysmon 1, Image `C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe`, CommandLine `powershell.exe -nop -w hidden -enc SQBFAFgAIAAoAE4AZQB3AC0ATwBiAGoAZQBjAHQA` | INC-WIN-POWERSHELL-ENCODE |
| 09:44:20 | sysmon.csv, PC-COMPTA07 | Sysmon 1, Image `C:\ProgramData\maj\outil.exe`, Hashes `MD5=<MD5 réservé>,SHA256=<SHA256 réservé>` | INC-WIN-OUTIL-OFFENSIF (par le hachage) |
| 09:44:31 | sysmon.csv, PC-COMPTA07 | Sysmon 10, SourceImage `C:\ProgramData\maj\outil.exe`, TargetImage `C:\Windows\system32\lsass.exe`, GrantedAccess `0x1010` | INC-WIN-ACCES-LSASS |
| 10:05:00 | security.json, SRV-FICHIERS | 1102, SubjectUserName `administrateur` | INC-WIN-JOURNAL-EFFACE |
| 10:06:30 | system.json, PC-COMPTA07 | 104, SubjectUserName `administrateur`, Channel `Security` | INC-WIN-JOURNAL-EFFACE |

Résultat : **16 détections**, au moins une par règle du catalogue minimal.

**Bénin interdit** (déclencherait une règle) : tout 4624 LogonType 10 ; 4720 ; 4728/4732/4756 vers un groupe d'administrateurs ; 1102 ; 104 ; 7045 ; 4698 ; Sysmon 10 visant lsass.exe ; ligne de commande avec `-e`/`-ec`/`-enc` suivi de ≥ 16 caractères base64 ; Sysmon 1 d'un outil listé ou du hachage réservé ; `Accepted … for root` ; `sudo` lançant un shell ou touchant `authorized_keys` ; `useradd` ; 5 `Failed password` d'une même IP, ou 5 4625 d'une même `IpAddress`, en 300 s.
**Bénin autorisé** : 4624 types 2/3/5, 4634, 4672, 4625 isolés, Sysmon 1 de processus courants, 7036, CRON, `Accepted publickey for deploy`, `sudo … COMMAND=/usr/bin/apt update`, `Invalid user` isolés.

## Rapport d'incident (CAP-6)

Ordre des sections et intitulés :

| # | Section | Contenu |
|---|---|---|
| 1 | Bandeau | « Démonstration — données fictives » |
| 2 | Synthèse | période `debut` → `fin` ; tableau des 4 sévérités dans l'ordre Critique, Élevée, Moyenne, Faible, zéros compris ; hôtes touchés (`actifs`) |
| 3 | Chronologie | tableau `Horodatage \| Hôte \| Fait \| Sévérité` : `debut.isoformat(timespec="seconds")`, `", ".join(hotes)`, `regle_titre`, libellé de sévérité ; une ligne par détection |
| 4 | Faits détectés | par récit : titre (`Recit.titre`) et `regle_id`, récit, impact, recommandation, références ATT&CK, preuves (les `max_preuves` premières : `fichier:ligne` et `" ".join(message.split())[:300]`, puis « + N autres »), statut et motifs |
| 5 | Indicateurs de compromission | tableau `Type \| Valeur \| Origines` (`", ".join(origines)`), identique à `RapportIncident.indicateurs` |
| 6 | Actifs touchés | liste `actifs` |
| 7 | Recommandations consolidées | liste `recommandations` |
| 8 | Annexe : sources analysées | tableau `Fichier \| Enregistrements examinés \| Ignorés` ; pour un JSON, mention « ligne = rang d'objet » |

Sans détection : sections 3 à 7 présentes, chacune avec la mention « Aucun fait détecté ».
