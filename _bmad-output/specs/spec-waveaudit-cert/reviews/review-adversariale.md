# Revue adversariale — SPEC-waveaudit-cert (C1 à C6), contrats §21-22, AD-17

Date : 2026-10-17. Relu : SPEC.md, formats-incident.md, stories.yaml, contrats §21-22, AD-0/1/8/15-17, et le socle réel sur `main` (11f33d8) : `domaine/modeles.py`, `ports.py`, `configuration.py`, `erreurs.py`, `application/config.py`, `tests/faux_moteur.py`, `tests/conftest.py`, `tests/unitaires/test_architecture.py`, `config/waveaudit.toml`, `.gitattributes`.

## Verdict

En l'état, C2, C3 et C4 lancés en parallèle cette nuit produiront chacun un code conforme à la lettre, mais la démo ne s'assemblera pas en C5. Le catalogue (conditions, seuils, noms de champs, hachage fictif) n'est fixé nulle part, alors que C2 écrit `attendu.yaml` et les lignes bénignes sans lui. `detection.py` (C3) doit appeler `indicateurs.py` (C4), écrit en parallèle. La composition ne permet pas « pas d'ouverture du moteur sans détection ». Le scénario `references_inventees` du faux moteur injecte des jetons que les garde-fous incident ne retirent pas. Il faut sept corrections critiques, toutes en texte de contrat, avant de lancer C1.

Le levier principal : **faire du catalogue et des champs une donnée normative créée par C1** (table de formats-incident.md, constantes `CHAMPS_*` dans `domaine/incident.py` et fixture canonique `tests/donnees/incident/canoniques.yaml`). C2 vérifie que son lecteur produit exactement ces événements, et C3 que ses règles se déclenchent exactement sur eux. La rencontre a lieu dans un fichier figé, pas dans la tête de deux agents.

---

## CRITIQUE

### K1. Le catalogue n'est pas normatif : C2 et C3 ne peuvent pas tomber d'accord

**Trou.** formats-incident.md ne donne, pour chaque règle, que l'identifiant et un indice (« 4625 », « `-enc` », « nom ou hachage d'outil connu »). Aucun seuil, aucune fenêtre, aucun champ `par`, aucun `log_name`, aucune expression régulière, aucun hachage. Pourtant C2 doit écrire `attendu.yaml` (`debut` de chaque rafale), placer au moins 60 % de lignes bénignes « qui ne doivent rien déclencher » et inventer le hachage de l'outil offensif. C3, lui, a pour consigne de « ne pas dépendre du jeu de démo de C2 ».

**Scénarios de divergence.**
- C2 met 6 échecs 4625 en 90 s. C3 choisit `seuil: 10, fenetre_s: 600` : aucune détection INC-WIN-FORCE-BRUTE.
- C2 invente `SHA256=DEADBEEF…` et C3 cherche `mimikatz` dans `Image` : aucune détection OUTIL-OFFENSIF.
- C2 met un 4624 LogonType 10 « bénin » d'un administrateur légitime : faux positif INC-WIN-CONNEXION-RDP, la règle étant sans agrégation.
- C2 met 4 échecs SSH bénins d'un utilisateur distrait. C3 choisit `seuil: 3` : faux positif.
- C3 compte à la fois `Invalid user X from` et `Failed password for invalid user X` : double comptage, la rafale démarre plus tôt que le `debut` de C2.
- `INC-LIN-CLE-SSH-AJOUTEE` : aucun journal natif ne trace l'ajout d'une clé. C2 l'écrit via `sudo … tee -a authorized_keys` alors que C3 cherche `message_regex: authorized_keys` sur `programme: sshd`.

**Correction.** Remplacer la liste « Catalogue minimal (15) » de formats-incident.md par la table normative ci-dessous. C3 reste libre des textes, des références (tant que `verifier_regles` passe) et des sévérités, mais pas des conditions ni de l'agrégation.

```markdown
### Catalogue minimal (15), conditions normatives

Conditions et agrégations figées : C3 les recopie telles quelles en YAML (chaînes entre apostrophes),
C2 construit le jeu de démo contre elles. Expressions évaluées par `re.search`, `re.IGNORECASE`.
Références et sévérités : valeurs conseillées, C3 peut les ajuster si `verifier_regles` passe.

| id | sév. | condition | agregation | réf. conseillées |
|---|---|---|---|---|
| INC-WIN-FORCE-BRUTE | elevee | log_name `Security`, event_id [4625] | seuil 5, fenetre_s 300, par [IpAddress] | T1110, T1110.001 |
| INC-WIN-CONNEXION-RDP | moyenne | log_name `Security`, event_id [4624], champs {LogonType: "10"} | — | T1021.001 |
| INC-WIN-COMPTE-CREE | moyenne | log_name `Security`, event_id [4720] | — | T1136.001 |
| INC-WIN-AJOUT-GROUPE-ADMIN | elevee | log_name `Security`, event_id [4728, 4732, 4756], champs_regex {TargetUserName: `^(administrateurs\|administrators\|admins du domaine\|domain admins\|administrateurs de l.entreprise\|enterprise admins)$`} | — | T1098 |
| INC-WIN-JOURNAL-EFFACE | critique | event_id [1102, 104] | — | T1070.001 |
| INC-WIN-SERVICE-INSTALLE | moyenne | log_name `System`, event_id [7045] | — | T1543.003 |
| INC-WIN-TACHE-PLANIFIEE | moyenne | log_name `Security`, event_id [4698] | — | T1053.005 |
| INC-WIN-POWERSHELL-ENCODE | elevee | event_id [1, 4688], champs_regex {CommandLine: `(?:^\|\s)[-/]e(?:c\|nc\|ncodedcommand)?\s+[a-z0-9+/=]{16,}`} | — | T1059.001, T1027 |
| INC-WIN-ACCES-LSASS | critique | log_name `Microsoft-Windows-Sysmon/Operational`, event_id [10], champs_regex {TargetImage: `\\lsass\.exe$`} | — | T1003.001 |
| INC-WIN-OUTIL-OFFENSIF | critique | log_name `Microsoft-Windows-Sysmon/Operational`, event_id [1], au_moins_un {Image: `\\(mimikatz\|rubeus\|sharphound\|lazagne)\.exe$`, Hashes: `SHA256=A1B2C3D4A1B2C3D4A1B2C3D4A1B2C3D4A1B2C3D4A1B2C3D4A1B2C3D4A1B2C3D4`} | — | T1588.002 |
| INC-LIN-SSH-FORCE-BRUTE | elevee | programme `sshd`, message_regex `^Failed password for ` | seuil 5, fenetre_s 300, par [ip] | T1110.001 |
| INC-LIN-SSH-CONNEXION-ROOT | elevee | programme `sshd`, message_regex `^Accepted \S+ for root from ` | — | T1078.003, T1021.004 |
| INC-LIN-SUDO-SHELL | elevee | programme `sudo`, champs_regex {commande: `^(?:/usr)?/bin/(?:(?:ba\|z\|da\|k)?sh\|su)(?:\s\|$)`} | — | T1548.003 |
| INC-LIN-COMPTE-CREE | moyenne | programme `useradd`, message_regex `^new user: ` | — | T1136.001 |
| INC-LIN-CLE-SSH-AJOUTEE | elevee | programme `sudo`, champs_regex {commande: `authorized_keys`} | — | T1098.004 |

Le hachage `A1B2C3D4…` (64 caractères) et son MD5 `A1B2C3D4A1B2C3D4A1B2C3D4A1B2C3D4` sont fictifs et réservés à l'outil offensif de la démo.

Lignes bénignes interdites dans le jeu de démo (elles déclencheraient une règle) : tout 4624 LogonType 10,
4720, 4728/4732/4756 vers un groupe d'administrateurs, 1102, 104, 7045, 4698, Sysmon 10 visant lsass.exe,
ligne de commande avec `-enc`/`-e <base64>`, `Accepted … for root`, `sudo` lançant un shell ou touchant
authorized_keys, `useradd`, et 5 `Failed password` ou 5 4625 ou plus d'une même IP en 300 s.
Autorisés : 4624 types 2/3/5, 4634, 4672, 4625 isolés, Sysmon 1 de processus courants, 7036, CRON,
`Accepted publickey for deploy`, `sudo … COMMAND=/usr/bin/apt update`, etc.
```

L'opérateur `au_moins_un` est nécessaire : la grammaire actuelle (« tous les critères doivent être vrais ») ne sait pas exprimer « nom **ou** hachage » (voir E6).

### K2. Les noms et valeurs de champs ne sont pas figés (Windows par événement, Linux par programme)

**Trou.** Pour Linux, §21 ne donne que la liste `utilisateur, ip, port, commande, nouvel_utilisateur, fichier_cible`, « extraits par motif », sans motif ni programme. Pour Windows, formats-incident.md liste quelques clés de `Data` avec « … », sans dire lesquelles portent quoi selon l'`Id`. La conversion des valeurs (`LogonType` entier en JSON, cellule vide en CSV) n'est pas définie non plus.

**Scénarios.**
- Dans `Failed password for invalid user admin from …`, C2 met `utilisateur = "invalid"` (premier mot après `for`) et C3 regroupe sur `utilisateur`.
- Pour `sudo`, C2 prend `utilisateur = root` (le `USER=`) et C4 sort le compte `root` au lieu de `deploy`.
- C2 nomme la cible du Sysmon 10 `Image` et C3 lit `TargetImage`.
- En JSON, `"LogonType": 10` donne `champs["LogonType"]` qui n'est pas une `str` : `ValidationError` sur `Evenement`, ou `"10.0"` si l'agent passe par un float.
- En CSV, `IpAddress` vide donne la clé avec la valeur `""`. En JSON, la clé est absente. L'agrégation `par [IpAddress]` diffère selon le format (voir K3).
- Une typo `IPAddress` dans une règle de C3 ne se déclenche jamais, et le test de C3, construit avec la même typo, passe.

**Correction (formats-incident.md, nouvelle section « Champs normalisés », et §21) :**

```markdown
### Champs normalisés (Evenement.champs)

Valeurs : `str` uniquement. Entier → `str(int)` ("10"), booléen → "true"/"false", objet ou liste →
`json.dumps(v, ensure_ascii=False, sort_keys=True)`. Valeur `null`, "" ou blanche → clé ABSENTE.
Aucune autre transformation (pas de strip interne, pas de changement de casse).

Windows : toutes les clés de `Data` (JSON) ou les colonnes hors tête (CSV) sont recopiées telles quelles.
Clés utilisées par les règles et les indicateurs, à respecter dans le jeu de démo :
| Id | LogName | Clés |
|---|---|---|
| 4624, 4625 | Security | TargetUserName, TargetDomainName, IpAddress, IpPort, LogonType, WorkstationName |
| 4720 | Security | TargetUserName (compte créé), SubjectUserName (créateur) |
| 4728, 4732, 4756 | Security | TargetUserName (= NOM DU GROUPE), MemberName (DN du membre), SubjectUserName |
| 4698 | Security | TaskName, SubjectUserName |
| 1102 | Security | SubjectUserName |
| 104 | System | SubjectUserName, Channel |
| 7045 | System | ServiceName, ImagePath, AccountName |
| 1 | Microsoft-Windows-Sysmon/Operational | Image, CommandLine, ParentImage, User, Hashes |
| 4688 | Security | NewProcessName, CommandLine, SubjectUserName |
| 10 | Microsoft-Windows-Sysmon/Operational | SourceImage, TargetImage, GrantedAccess, SourceUser |

Linux : `programme` = nom avant `[pid]`, casse conservée. `message` = texte après `programme[pid]: `, `strip()`.
Champs, extraits par `re.search` sur `message` selon `programme` (autres programmes : champs vides) :
| programme | motif | champs |
|---|---|---|
| sshd | `^(?:Failed\|Accepted) \S+ for (?:invalid user )?(?P<utilisateur>\S+) from (?P<ip>\S+) port (?P<port>\d+)` | utilisateur, ip, port |
| sshd | `^Invalid user (?P<utilisateur>\S+) from (?P<ip>\S+)(?: port (?P<port>\d+))?` | utilisateur, ip, port |
| sudo | `^(?P<utilisateur>\S+) : .*?\bCOMMAND=(?P<commande>.+)$` | utilisateur (l'appelant, jamais USER=), commande |
| sudo | dans `commande` : `(?P<fichier_cible>/\S*authorized_keys2?)` | fichier_cible |
| useradd | `new user: name=(?P<nouvel_utilisateur>[^,\s]+)` | nouvel_utilisateur |
```

Et dans `domaine/incident.py` (C1), les constantes que `verifier_regles` (C3) et les tests du lecteur (C2) utilisent :

```python
CHAMPS_LINUX = frozenset({"utilisateur", "ip", "port", "commande", "nouvel_utilisateur", "fichier_cible"})
CHAMPS_WINDOWS = frozenset({"TargetUserName", "TargetDomainName", "SubjectUserName", "IpAddress", "IpPort",
    "LogonType", "WorkstationName", "MemberName", "TaskName", "Channel", "ServiceName", "ImagePath",
    "AccountName", "Image", "CommandLine", "ParentImage", "User", "Hashes", "NewProcessName",
    "SourceImage", "TargetImage", "GrantedAccess", "SourceUser"})
```

`verifier_regles` rejette une clé de `champs`, `champs_regex`, `au_moins_un` ou `agregation.par` absente de `CHAMPS_<source>`.

### K3. La sémantique de l'agrégation est indécidable

**Trou.** « Fenêtre glissante. Une détection couvre la rafale maximale ; la rafale suivante ne commence qu'après la fin de la précédente. » Trois lectures au moins :
- (a) chaînage : on prolonge tant que l'écart entre deux événements consécutifs reste ≤ fenêtre, ce qui donne une durée sans borne ;
- (b) fenêtre fixe ancrée sur le premier événement ;
- (c) fenêtre glissante avec seuil maintenu.

Restent ouverts aussi : le point de départ (le premier événement du groupe ou le premier de la fenêtre qui atteint le seuil), la borne (`<` ou `<=`), le traitement d'un champ `par` absent, la casse des clés de groupe et le contenu de `evenements`.

**Scénario.** 8 échecs SSH, un toutes les 60 s, avec seuil 5 et fenêtre 300.
- Lecture (b) : une détection de 5 événements, puis 3 restants sans détection.
- Lecture (a) : une détection de 8 événements.
- Lecture (c) : 8 événements, ou bien une rafale qui commence au 1er et une autre au 6e selon l'implémentation.

C2 écrit `debut` et C5 compte les détections : l'une des deux échoue. Avec `par [IpAddress]`, un 4625 sans IP est regroupé sous `""` chez l'un et ignoré chez l'autre.

**Correction (§21, puce « Détection », à coller) :**

```markdown
- Applicabilité : une règle ne s'applique qu'aux événements de même `source`. Critères :
  `event_id` (appartenance), `log_name` et `programme` (égalité `casefold`), `champs` (clé présente ET
  valeur égale en `casefold`), `champs_regex` (clé présente ET `re.search`), `au_moins_un` (au moins une
  clé présente dont la valeur vérifie `re.search`), `message_regex` (`re.search`). Clé absente = critère
  faux. Toutes les regex en `re.IGNORECASE`. Condition sans aucun critère : refusée par `verifier_regles`.
- Sans agrégation : une détection par événement ; `debut = fin = horodatage`, `hotes = [hote]`.
- Avec agrégation : on garde les événements qui ont TOUS les champs `par` (sinon ils sont écartés de la
  règle), groupés par le tuple des valeurs en `casefold` (`par: []` = un seul groupe). Dans chaque
  groupe, événements triés par `(horodatage, fichier, ligne)`, indices 0..n-1, `t` en secondes,
  « dans la fenêtre » signifie `t_k - t_j <= fenetre_s` (borne incluse) :
      i = 0
      tant que i < n :
          k = plus petit indice >= i tel que #{j : i <= j <= k et t_k - t_j <= fenetre_s} >= seuil
          si aucun k : arrêter
          d = plus petit j >= i tel que t_k - t_j <= fenetre_s
          f = k
          tant que f + 1 < n et #{j : d <= j <= f+1 et t_{f+1} - t_j <= fenetre_s} >= seuil : f += 1
          détection : evenements = groupe[d..f], debut = t_d, fin = t_f, hotes = valeurs distinctes triées
          i = f + 1
  Vecteurs de test obligatoires (seuil 3, fenêtre 60) : t = 0,10,20,100,110,120 → 2 détections
  [0..20] et [100..120] ; t = 0,10,70,80,90 → 1 détection [70..90] (0 et 10 perdus) ;
  t = 0,30,60 → 1 détection (borne incluse) ; t = 0,30,61 → aucune.
- `Detection.indicateurs` vaut `[]` en sortie de `detecter` (voir K5).
- Tri final : `(debut, regle_id, evenements[0].fichier, evenements[0].ligne)`.
```

### K4. `attendu.yaml` n'a pas de schéma, et il se trouve dans le dossier lu

**Trou.** La story C2 dit seulement « liste des détections attendues : regle_id, debut, hote ; liste exacte des indicateurs attendus ». Rien ne fixe :
- le format de `debut` (avec ou sans fuseau, en UTC ou non) ;
- `hote` au singulier alors que `Detection.hotes` est une liste ;
- la comparaison par égalité de chaîne ou d'instant ;
- l'année des lignes syslog ;
- les lignes volontairement illisibles ;
- ce que C5 peut modifier.

Le fichier se trouve dans `donnees/demo/incident/`, c'est-à-dire le dossier passé à `waveaudit incident`. Or aucune règle ne dit qu'un `.yaml` est ignoré.

**Scénarios.**
- C2 écrit `debut: 2026-10-14 08:02:10` sans fuseau, que YAML lit comme un `datetime` naïf : comparer à un `AwareDatetime` lève `TypeError`.
- C2 écrit `hote: bastion01` alors que l'événement porte `BASTION01`.
- Le lecteur de C2 range `attendu.yaml` dans `LigneIgnoree`, ce qui fausse l'annexe des sources.
- C5, face à 3 indicateurs d'écart, recopie la sortie dans `attendu.yaml` : le test devient tautologique, sans enfreindre « ne jamais affaiblir le test » à la lettre.

**Correction (formats-incident.md, nouvelle section, à coller) :**

```markdown
## Jeu de démonstration et oracle (CAP-3, CAP-4)

Dossier `donnees/demo/incident/` : `security.json`, `system.json`, `sysmon.csv`, `auth.log`, `syslog`
et `attendu.yaml`. Un fichier non routé (`.yaml`, `.md`, `.gitkeep`…) est ignoré en silence : ni
événement, ni `LigneIgnoree`, ni entrée dans `fichiers`.

attendu.yaml (UTF-8, horodatages en CHAÎNES ISO 8601 avec fuseau, entre guillemets) :
    annee: 2026                       # à passer en RequeteIncident.annee
    decalage_syslog: "+02:00"         # doit égaler config.incident.decalage_syslog
    detections:                       # triées comme detecter : (debut, regle_id)
      - regle_id: INC-LIN-SSH-FORCE-BRUTE
        debut: "2026-10-14T08:02:10+02:00"
        fin: "2026-10-14T08:03:20+02:00"
        hotes: [BASTION01]            # égalité exacte avec Detection.hotes
        nb_evenements: 8
    indicateurs:                      # liste exacte, triée par (type, valeur), valeurs normalisées
      - {type: ip, valeur: 203.0.113.45}
    ignorees:                         # lignes volontairement illisibles du jeu
      - {fichier: auth.log, ligne: 57}

Comparaison (C5) : `debut`/`fin` par égalité d'instants (`datetime.fromisoformat`), le reste par
égalité exacte. La liste des détections produites, projetée sur ces champs, est ÉGALE à la liste
attendue (ni manquante, ni en trop). Ensemble des (type, valeur) égal. `ignorees` égal.
Part bénigne : (événements lus hors de toute détection) / (événements lus) >= 0,60, testée par C5.

Modification par C5 : `attendu.yaml` ne peut changer que là où il contredit formats-incident.md ou
§21 (règle de calcul), avec le motif cité dans le message de commit ; jamais pour recopier une sortie.
Une détection attendue ne peut être retirée que si la ligne de démo correspondante est corrigée.
```

La chronologie normative recommandée (ci-dessous, en E6) permet à C2 de calculer `debut`, `fin` et `nb_evenements` à la main avec l'algorithme de K3.

### K5. `detection.py` (C3) doit remplir `indicateurs` avec `indicateurs.py` (C4), codé en parallèle

**Trou.** §21 dit « `indicateurs` est rempli par `domaine/indicateurs.py` » dans la puce Détection. C3 et C4 tournent dans des worktrees séparés : `waveaudit.domaine.indicateurs` n'existe pas dans celui de C3.

**Scénarios.**
- C3 écrit son propre `domaine/indicateurs.py` minimal : conflit de fusion avec C4 sur le même fichier.
- C3 importe le module manquant : ses tests échouent.
- C3 laisse `[]` et C5 ne sait pas qui remplit les indicateurs.

**Correction (§21) :** remplacer « `indicateurs` est rempli par `domaine/indicateurs.py` » par :

> `detecter` ne remplit pas `indicateurs` (liste vide) et n'importe pas `domaine.indicateurs`. Le pipeline (C5) complète chaque détection : `d.model_copy(update={"indicateurs": extraire(d.evenements)})`.

Ajouter à `invoke_dev_with` de C3 : « detection.py n'importe ni ne crée domaine/indicateurs.py ».

### K6. La composition contredit « sans détection, pas d'ouverture du moteur », et l'exporteur n'existe qu'en C6

**Trou.** `ouvrir_incident(config, modele) -> ContextManager[tuple[PortsIncident, InfoMoteur]]` démarre le moteur (`llama-server` en `local-gere`). Or `PortsIncident` porte aussi `source_journaux` et `regles`, nécessaires **avant** de savoir s'il y a une détection. Autre manque : `PortsIncident.exporteur` est obligatoire, mais `export_incident_docx.py` n'arrive qu'en C6, alors que C5 doit écrire `rapport-incident.docx`.

**Scénarios.**
- C5 ouvre la composition pour lire les journaux, ce qui démarre le moteur même sur un dossier sans détection, en violation de CAP-7 (« code 3 seulement s'il y a au moins une détection »).
- C5 instancie un adaptateur de lecture hors de `composition.py` : `test_adaptateurs_instancies_par_la_composition_seule` échoue.
- C5 invente un faux exporteur dans `adaptateurs/` que C6 remplace : du code mort, et un test e2e de C5 qui ne vérifie pas le .docx.

**Correction (§21, ports et service) :**

```python
@dataclass(frozen=True)
class PortsIncident:                      # aucun processus, aucune connexion
    source_journaux: SourceJournaux; regles: CatalogueRegles; exporteur: ExporteurIncident
# application/composition.py (C5) :
def creer_ports_incident(config: Configuration) -> PortsIncident: ...
def ouvrir_moteur_incident(config: Configuration, modele: str | None
    ) -> ContextManager[tuple[Moteur, str, InfoMoteur]]: ...   # (moteur, prefixe_systeme, info)
```

> `executer_incident` lit et détecte avec `creer_ports_incident`. Il n'appelle `ouvrir_moteur_incident` (puis `sonder`) que s'il y a au moins une détection. C5 peut extraire de `ouvrir` une fonction privée commune, sans en changer le comportement (`tests/e2e/test_lot.py` reste vert).

Et **découper C6** : C6a = `adaptateurs/export_incident_docx.py` et `test_export_incident.py`. Elle ne dépend que des formes de C1 et peut tourner **en parallèle de C2-C4**. C6b = CLI, test hors ligne et README, après C5. C5 branche alors le vrai exporteur.

### K7. `references_inventees` en mode incident n'est pas retiré par les garde-fous incident, et CAP-5 n'est pas couvert

**Trou.** §21 : « Les autres scénarios s'appliquent de la même façon ». Le faux moteur actuel ajoute `" CWE-9999 CVE-2099-0001 https://exemple.invalid/x"` à `description`. En mode incident, le schéma n'a pas `description` mais `recit`, et les garde-fous incident ne retirent **que** `T\d{4}…`, les IP et les hachages. Le test C5 « references_inventees (retirées) » est donc impossible, ou bien l'agent étend les garde-fous à CWE et aux URL hors contrat. CAP-5 exige au contraire « une IP, un hachage ou une technique ATT&CK inventés retirés », et aucun scénario ne les injecte. `vecteur_invalide` n'a pas de sens pour un récit.

**Correction (§21, puce Prompt, et §13) :**

```markdown
- Mode incident du faux moteur (balise `<regle>` présente, `<constat>` absente) :
  - `nominal` : {titre, recit, impact, recommandation} = "[adapté] " + {titre, description, impact,
    recommandation} de la règle ; aucune clé `cvss`.
  - `references_inventees` : nominal, avec `REFERENCES_INVENTEES_INCIDENT =
    " T9999 T1110.999 203.0.113.254 " + "0f" * 32` ajouté à `recit`. Attendu après garde-fous :
    2 motifs `reference_retiree` (T9999, T1110.999) et 2 motifs `indicateur_retire`.
    203.0.113.254 et 0f0f… sont réservés : interdits dans le jeu de démo.
  - `vecteur_invalide` : identique à `nominal`. `json_invalide`, `json_invalide_une_fois`, `lent`,
    `erreur_500`, `injoignable` : inchangés.
  - Ni `<regle>` ni `<constat>` : réponse `SANS_CONSTAT` (inchangée).
```

---

## ÉLEVÉ

### E1. `incident.regles` n'est résolu ni par `charger_configuration`, ni par `config_test`

**Trou.** `application/config.py` ne résout que `[chemins]` contre `racine_projet()`, et `config_test` ne réécrit que `donnees["chemins"]`. `[incident].regles = "donnees/regles"` reste donc relatif au **dossier courant**. Par ailleurs, `application/config.py` ne figure pas dans la liste des fichiers que C1 peut modifier.

**Scénario.** Les tests passent depuis la racine du dépôt. `waveaudit incident` lancé depuis un autre dossier, ou un test CLI de C6 qui fait `chdir(tmp_path)`, donne « règles introuvables » et le code 2. C5 « corrige » alors en résolvant dans la composition, ce qui fait un second lieu de résolution des chemins (contraire à AD-13).

**Correction (§21, bloc TOML) :** déplacer le chemin dans `[chemins]`, déjà résolu partout :

```toml
[chemins]
regles = "donnees/regles"      # ajouté par C1 (ConfigChemins.regles: Path = Path("donnees/regles"))
[incident]
decalage_syslog = "+02:00"     # fixe, sans heure d'été ; motif ^[+-]\d{2}:\d{2}$ validé
max_preuves = 10               # >= 1
longueur_max_recit = 1500      # >= 100
```

### E2. `Evenement.ligne`, `LectureJournaux.fichiers` et le routage sont flous

**Trou et scénarios.**
- **CSV** : `Message` exporté par `Get-WinEvent` est multiligne entre guillemets. Selon l'agent, `ligne` vaut l'index de l'enregistrement (1, 2…), le `reader.line_num` (ligne de **fin** de l'enregistrement) ou la ligne de début. Les `origines` de `attendu.yaml` divergent.
- **JSON** : « index 1-based » est clair, mais le rapport affiche `security.json:42`, alors que la ligne 42 du fichier n'est pas le 42e objet.
- **JSON invalide** ou non tableau (NDJSON, objet seul) : non défini.
- `fichiers` : lignes physiques, enregistrements, ou événements seulement ?
- Lignes vides du syslog : `LigneIgnoree` ou non ?
- `auth.log.2.gz` : 3 000 lignes illisibles.
- `Security.JSON` ou `AUTH.LOG` : le routage dépend de la casse.
- L'ordre de lecture des fichiers suit `os.listdir`.

**Correction (§21, puce Lecture, à coller) :**

```markdown
- Fichiers du dossier (sans sous-dossiers, fichiers cachés exclus) triés par `nom.casefold()`. Routage
  insensible à la casse : suffixe `.json`/`.csv` → Windows ; sinon nom `auth.log*`, `syslog*`,
  `secure*` ou suffixe `.log` → Linux ; suffixe `.gz`, `.zip`, `.bz2`, `.xz` et tout autre fichier :
  ignoré en silence.
- `Evenement.fichier` = nom seul (même validateur que `Note.fichier`).
- JSON : `utf-8-sig` ; la racine doit être un tableau. Sinon, ou si le JSON est invalide : une seule
  `LigneIgnoree(ligne=1)`. `ligne` = rang 1-based de l'objet dans le tableau. Élément non objet, sans
  `TimeCreated` ISO avec fuseau, ou sans `Id` entier : `LigneIgnoree` à ce rang.
- CSV : `utf-8-sig`, `newline=""`. Séparateur `;` si la ligne d'en-tête en contient plus que de `,`.
  En-tête sans `TimeCreated` ou `Id` : une `LigneIgnoree(ligne=1)`. `ligne` = numéro de ligne physique
  où COMMENCE l'enregistrement (en-tête = 1, premier enregistrement = 2). Enregistrement vide sauté.
- Syslog : `utf-8` avec `errors="replace"` ; `\r` final retiré ; ligne vide sautée et non comptée.
- `fichiers[nom]` = événements + lignes ignorées de ce fichier (enregistrements examinés).
- Le rapport cite `fichier:ligne` ; pour un JSON, l'annexe précise « rang d'objet ».
```

### E3. L'extraction d'indicateurs produira de faux IOC, ou des IOC que C2 n'aura pas prévus

**Trous et scénarios.**
- 4728/4732/4756 : `TargetUserName` contient le **nom du groupe**, d'où un compte « Administrateurs » dans le tableau des IOC.
- `SubjectUserName = "SRV-FICHIERS$"` (compte machine, présent dans 4688 et 4698) devient un compte IOC.
- `Hashes = "SHA1=…,MD5=…,SHA256=…,IMPHASH=…"` : rien ne dit si la valeur est `sha256=abc…` ou `abc…`, ni si IMPHASH est écarté.
- La recherche d'IPv4 dans `message` attrape `10.0.17763.1` (version Windows), `0.0.0.0` et les adresses présentes dans la ligne de commande PowerShell.
- `IpAddress = "::ffff:192.0.2.10"` (fréquent en 4624/4625) : l'IPv6 n'est pas reconnue comme IP, ou bien elle crée une seconde IP.
- « Minuscules sauf comptes » : `Admin` et `admin` donnent deux comptes.
- Ordre de `origines` non défini.
- L'union pour le rapport : `Evenement` est `frozen` avec un `dict`, donc `hash(evenement)` lève `TypeError` (vérifié avec pydantic sur ce dépôt). Un `set(evenements)` plante.
- Le Sysmon 10 (accès à LSASS) ne donne aucun exécutable, `SourceImage` n'étant pas une source. Le 7045 ne donne pas `ImagePath`, l'IOC le plus utile.

**Correction (§21, puce Indicateurs, à coller) :**

```markdown
- Sources : ip ← `IpAddress`, `ip`, IPv4 de `message` ; compte ← `TargetUserName` (sauf event_id
  4728/4732/4756), `SubjectUserName`, `utilisateur`, `nouvel_utilisateur` ; executable ← `Image`,
  `SourceImage`, `ImagePath` ; hachage ← `Hashes` ; hote ← `Evenement.hote`.
- `Hashes` : découpé sur `,`, puis `ALGO=valeur` ; seuls MD5 (32), SHA1 (40) et SHA256 (64 hex) gardés,
  valeur seule, en minuscules ; IMPHASH et valeur non hexadécimale ignorés.
- IP : candidat validé par `ipaddress.ip_address` ; IPv4 mappée (`::ffff:a.b.c.d`) → IPv4 ; IPv4 dans
  `message` par `(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])` puis validation. Exclues : non valides,
  `0.0.0.0`, `127.0.0.0/8`, `::1`, `::`.
- Comptes exclus (comparaison `casefold` après strip) : vide, `-`, `SYSTEM`, `LOCAL SERVICE`,
  `NETWORK SERVICE`, `ANONYMOUS LOGON`, et toute valeur finissant par `$`. Casse conservée ; les
  doublons sont repérés en `casefold`, et l'on garde la graphie du premier événement dans l'ordre
  `(horodatage, fichier, ligne)`.
- Exécutables : minuscules, chemin complet tel quel. Hôtes : minuscules.
- `origines` : `f"{fichier}:{ligne}"` distinctes, triées par `(fichier, ligne)` numérique.
- Union pour le rapport : événements dédoublonnés par la clé `(fichier, ligne)` (Evenement n'est pas
  hachable).
```

C2 calcule la liste exacte de `attendu.yaml` avec ces règles, **messages compris** : une IP présente dans le `Message` français d'un 4624 ou dans une ligne de commande compte.

### E4. Les garde-fous du récit sont trop vagues pour converger, et ils peuvent dégrader le nominal

**Trous et scénarios.**
- Les motifs IPv6 et hachage ne sont pas donnés. Un `[0-9a-f:]{2,}` naïf retire « 08:02:10 » d'un récit : le texte est mutilé et passe en `a_revoir`. Un MD5 `[0-9a-f]{32}` attrape le milieu d'un SHA256.
- La comparaison avec les indicateurs ne précise pas la casse : le SLM écrit le hachage en majuscules, l'indicateur est en minuscules, et le hachage légitime est retiré.
- `T1110` est cité alors que la règle n'a que `T1110.001` : retiré ou non ?
- Les textes types de C3 qui citent « T1059 » ou « 127.0.0.1 » sont retirés en mode nominal, donc le e2e de C5 sort tout en `a_revoir`.
- Une rubrique de « moins de 20 caractères » est complétée, mais les titres de règles font souvent moins de 20 caractères (« Compte créé », 11). Avec un vrai SLM, chaque titre court est remplacé par un titre type tout aussi court, et toutes les détections passent en `a_revoir`.

**Correction (§21, puce Garde-fous) :**

```markdown
- Rubriques traitées : titre, recit, impact, recommandation. Ordre : (1) références = celles de la règle ;
  (2) jetons `(?<![A-Za-z0-9])T\d{4}(?:\.\d{3})?(?![\d.])` (IGNORECASE) gardés si `upper()` ∈ ids des
  références de la règle (égalité exacte : T1110 ≠ T1110.001), sinon retirés (`reference_retiree`) ;
  (3) IPv4 (motif de E3), IPv6 (`(?<![0-9A-Fa-f:])[0-9A-Fa-f:]*:[0-9A-Fa-f:]*:[0-9A-Fa-f:.]*` puis
  validation `ipaddress`, sinon laissé), hachages `(?<![0-9A-Fa-f])(?:[0-9A-Fa-f]{64}|[0-9A-Fa-f]{40}|
  [0-9A-Fa-f]{32})(?![0-9A-Fa-f])` : gardés si leur forme normalisée (minuscules, IPv4 mappée) est la
  valeur d'un indicateur de la détection, sinon retirés (`indicateur_retire`, jeton dans `detail`) ;
  espaces normalisés, `()` et `[]` vides supprimés ; (4) rubrique vide ou, hors `titre`, de moins de
  20 caractères → texte type (`rubrique_completee`) ; `titre` seulement si vide ; troncature à
  `longueur_max` ; (5) `statut = a_revoir` ssi motifs.
- Repli : `titre/recit/impact/recommandation` = `titre/description/impact/recommandation` de la règle,
  passés à `appliquer_recit` avec `motifs_initiaux=[repli_…]`.
- La troncature des preuves à `max_preuves` n'est PAS un motif.
```

Et dans `verifier_regles` (C3) : `titre`, `description`, `impact` et `recommandation` ne contiennent aucun jeton ATT&CK, IPv4, IPv6 ni hachage, et `description`, `impact` et `recommandation` font au moins 20 caractères. Les motifs sont **dans `domaine/incident.py` (C1)** (`MOTIF_TECHNIQUE`, `MOTIF_IPV4`, `MOTIF_HACHAGE`), pour que C3 et C4 utilisent les mêmes.

### E5. La chronologie déterministe est impossible avec les formes actuelles, et personne n'assemble le rapport

**Trou.** La colonne « Fait » de la chronologie doit être déterministe (Constraints), mais `Recit` ne porte que `titre`, produit par le SLM. Le titre de la règle n'est nulle part dans `RapportIncident`. De plus, aucune story ne dit qui calcule `RapportIncident`, ni comment : `debut`, `fin`, `actifs`, `recommandations` (texte type ou texte adapté, et dans quel ordre), le format de la cellule « Origines », la mention « Aucun fait détecté ».

**Scénario.** C6 affiche `Recit.titre` (« [adapté] Force brute SSH ») et C5 compare au titre de la règle. Autre cas : C5 met les recommandations adaptées par le SLM, dédoublonnées par égalité exacte, et rien ne se dédoublonne.

**Correction (§21) :** ajouter `regle_titre: str` à `Recit` (copié de la règle par `appliquer_recit`), puis :

```markdown
- `workflows/incident/pipeline.py` (C5) : `assembler_rapport(lecture, recits) -> RapportIncident` :
  `debut`/`fin` = min des `debut` / max des `fin` (None sans détection) ; `recits` dans l'ordre des
  détections ; `indicateurs` = `extraire(union)` (E3) ; `actifs` = hôtes distincts de toutes les
  détections, triés `casefold` ; `recommandations` = `recommandation` TYPE de chaque règle, dans l'ordre
  des détections, dédoublonnées à l'égalité ; `sources = lecture.fichiers` ; `ignorees = lecture.ignorees`.
- Rapport Word : Chronologie « Fait » = `regle_titre`, « Hôte » = `", ".join(hotes)`, « Horodatage » =
  `debut.isoformat(timespec="seconds")` ; Synthèse : les 4 sévérités dans l'ordre critique, elevee,
  moyenne, faible, zéros compris ; Indicateurs « Origines » = `", ".join(origines)` ; sans détection,
  sections 3 à 7 présentes avec la mention « Aucun fait détecté ».
```

### E6. Le scénario de démo exige des fichiers et des opérateurs que la spec ne prévoit pas

**Trous.**
- 7045 (service) et 104 (journal effacé) sont dans le journal **System**, mais la liste de C2 ne prévoit que `security.json` et `sysmon.csv`. C2 mettra un `LogName: System` dans `security.json`, ou omettra ces lignes.
- « Nom ou hachage » de l'outil offensif ne peut pas s'exprimer quand tous les critères doivent être vrais (K1).
- Le récit (« connexion » après la force brute SSH, puis « sudo vers un shell ») ne dit pas qui se connecte en root. Pourtant `INC-LIN-SSH-CONNEXION-ROOT` doit avoir une détection attendue, et le hachage fictif doit être connu de C3.

**Correction.** Dans `Condition` (C1) : `au_moins_un: dict[str, str] = {}`. Dans la liste de C2 : `system.json`. Ajouter à formats-incident.md la chronologie d'attaque normative (C2 l'entoure de bénin, sans modifier ces lignes), le 2026-10-14, en `+02:00` :

| Heure | Fichier, hôte | Ligne d'attaque | Détection |
|---|---|---|---|
| 08:02:10 → 08:03:20 | auth.log, BASTION01 | 8 × `sshd[…]: Failed password for invalid user admin from 203.0.113.45 port 410xx ssh2`, toutes les 10 s | LIN-SSH-FORCE-BRUTE (8 év.) |
| 08:03:41 | auth.log | `sshd: Accepted password for deploy from 203.0.113.45 port 41022 ssh2` | aucune |
| 08:05:02 | auth.log | `sudo:   deploy : TTY=pts/0 ; PWD=/home/deploy ; USER=root ; COMMAND=/bin/bash` | LIN-SUDO-SHELL |
| 08:07:15 | auth.log | `useradd[2311]: new user: name=maintenance, UID=1002, GID=1002, home=/home/maintenance, shell=/bin/bash` | LIN-COMPTE-CREE |
| 08:09:40 | auth.log | `sudo:   deploy : TTY=pts/0 ; PWD=/home/deploy ; USER=root ; COMMAND=/usr/bin/tee -a /root/.ssh/authorized_keys` | LIN-CLE-SSH-AJOUTEE |
| 08:12:03 | auth.log | `sshd: Accepted publickey for root from 203.0.113.45 port 41100 ssh2` | LIN-SSH-CONNEXION-ROOT |
| 09:14:00 → 09:15:15 | security.json, SRV-FICHIERS | 6 × 4625, TargetUserName `administrateur`, IpAddress `192.0.2.10`, LogonType 10, toutes les 15 s | WIN-FORCE-BRUTE (6 év.) |
| 09:15:40 | security.json | 4624, LogonType 10, `administrateur`, `192.0.2.10` | WIN-CONNEXION-RDP |
| 09:20:11 | security.json | 4720, TargetUserName `svc-maj`, SubjectUserName `administrateur` | WIN-COMPTE-CREE |
| 09:20:45 | security.json | 4732, TargetUserName `Administrateurs`, MemberName `CN=svc-maj,CN=Users,DC=corp,DC=exemple,DC=test` | WIN-AJOUT-GROUPE-ADMIN |
| 09:23:10 | system.json, SRV-FICHIERS | 7045, ServiceName `MajCorp`, ImagePath `C:\ProgramData\maj\maj.exe` | WIN-SERVICE-INSTALLE |
| 09:24:30 | security.json | 4698, TaskName `\MiseAJourCorp` | WIN-TACHE-PLANIFIEE |
| 09:41:02 | sysmon.csv, PC-COMPTA07 | Sysmon 1, `powershell.exe -nop -w hidden -enc SQBFAFgAIAAoAE4AZQB3AC0ATwBiAGoAZQBjAHQA…` | WIN-POWERSHELL-ENCODE |
| 09:44:20 | sysmon.csv, PC-COMPTA07 | Sysmon 1, Image `C:\ProgramData\maj\outil.exe`, Hashes `MD5=A1B2…(32),SHA256=A1B2…(64)` | WIN-OUTIL-OFFENSIF (par le hachage) |
| 09:44:31 | sysmon.csv, PC-COMPTA07 | Sysmon 10, SourceImage `C:\ProgramData\maj\outil.exe`, TargetImage `C:\Windows\system32\lsass.exe`, GrantedAccess `0x1010` | WIN-ACCES-LSASS |
| 10:05:00 | security.json, SRV-FICHIERS | 1102 | WIN-JOURNAL-EFFACE |
| 10:06:30 | system.json, PC-COMPTA07 | 104 | WIN-JOURNAL-EFFACE |

Le résultat attendu est de 16 détections (17 lignes ou rafales d'attaque, dont la connexion de `deploy` qui ne déclenche rien), une au moins par règle. Le nom d'hôte est écrit `BASTION01` dans le syslog et dans `MachineName` (nom court, jamais un FQDN). `Evenement.hote` reste verbatim.

### E7. Préconditions de la nuit : `main` ne contient que le socle, et V1 touche les mêmes fichiers que C1

**Constat.** Sur `main` (11f33d8), seuls `domaine/`, `application/config.py`, `interfaces/cli.py` (squelette) et les tests du socle existent. Il manque `lot.py`, `composition.py`, `moteur_openai`, `garde_reseau`, `export_docx` (bandeau) et le registre. Or C5 et C6 en dépendent : `nouvel_id_lot`, l'écrivain de `journal.jsonl`, `ouvrir`, le garde et le bandeau. Par ailleurs :
- AD-8 fait de `lot.py` le **seul** écrivain de `journal.jsonl`, et la story 12 n'expose pas d'écrivain public ;
- V1 (§22) modifie `configuration.py`, `waveaudit.toml` et `moteur_openai`, comme C1 pour les deux premiers.

**Correction.**
- Lancer C1 seulement sur un `main` qui contient les stories 2 à 16, avec V1 déjà fusionnée ou planifiée **après** C1.
- Ajouter à C5 : « extraire de `application/lot.py` une fonction publique `ecrire_evenement(chemin_journal, evenement)` (ou une classe `JournalLot`) utilisée par `lot.py` et `incident.py`, sans changer le comportement (`test_lot.py` vert) ».
- Pour les événements, réutiliser `lot_demarre` (`total` = nombre de détections, `details` = `{"workflow": "incident"}` + `pid_moteur` s'il existe), puis `fiche_demarree` et `fiche_terminee` (`note` = `regle_id`, `statut` = ok/a_revoir), puis `lot_termine` et `lot_echoue`. Aucun nouveau `TypeEvenement`.

### E8. Les validations que C1 doit poser ne sont pas listées

« validations » dans C1 est trop vague. Sans elles, C3 et C4 écrivent des modèles plus laxistes dans leurs tests. À coller dans §21 :

```markdown
Toutes les formes : `ConfigDict(extra="forbid", frozen=True)`. Validations :
- Evenement : `ligne >= 1` ; `fichier` nom seul ; `champs` dict[str, str] (Evenement non hachable :
  dédoublonner par (fichier, ligne)).
- Condition : au moins un critère non vide ; `au_moins_un: dict[str, str] = {}`.
- Agregation : `seuil >= 2`, `fenetre_s >= 1`, `par: list[str] = []`.
- Regle : `references` min_length=1 ; `id` correspond à `^INC-(WIN|LIN)-[A-Z0-9]+(-[A-Z0-9]+)*$`.
- Detection : `debut <= fin` ; `evenements` non vide.
- Indicateur : `origines` non vide.
- Recit : `regle_titre: str` ; statut a_revoir ssi motifs (même validateur que Fiche).
- ConfigIncident : `decalage_syslog` motif `^[+-]\d{2}:\d{2}$`, `max_preuves >= 1`.
```

---

## MOYEN

### M1. Parsing syslog : formats réels non couverts

- Jour sur un espace de remplissage (`Oct  5`), `[pid]` facultatif (`sudo:`, `kernel:`), message de `sudo` précédé d'espaces.
- Mois en anglais : `strptime("%b")` dépend de la locale (sur un Windows français, `setlocale` appelé par une bibliothèque casse le parsing). Il faut une table fixe `{"Jan":1,…}`.
- `29 févr.` hors année bissextile : `LigneIgnoree`.
- **rsyslog moderne** (Debian 12, Ubuntu 24.04) : `2026-10-14T08:02:10.123456+02:00 bastion01 sshd[812]: …`. Sans prise en charge, tout `auth.log` récent est ignoré.
- Correction à coller : « Motif `^(?P<mois>[A-Z][a-z]{2}) {1,2}(?P<jour>\d{1,2}) (?P<heure>\d{2}:\d{2}:\d{2}) (?P<hote>\S+) (?P<prog>[^\s:\[]+)(?:\[\d+\])?: ?(?P<message>.*)$`, mois par table anglaise fixe. Une ligne commençant par un horodatage ISO 8601 avec fuseau est aussi acceptée : année et fuseau sont alors ceux de la ligne. Année croissante : dans un même fichier, si le mois d'une ligne est **inférieur** à celui de la ligne précédente acceptée, l'année est incrémentée ; jamais de décrément. »

### M2. Décalage fixe et heure d'été

`decalage_syslog = "+02:00"` est faux pour des journaux de novembre à mars en France. Il faut le documenter comme limite connue : « décalage fixe, sans heure d'été ; pour un incident à cheval sur un changement d'heure, lancer deux analyses ». L'écrire dans le README (C6b) et dans `Assumptions`. Ne pas passer par `zoneinfo` : dépendance `tzdata` sous Windows, et résultat dépendant de la machine.

### M3. Exports Windows réels

- PowerShell 5.1 : `ConvertTo-Json | Out-File` écrit en **UTF-16 LE avec BOM**. Lu en `utf-8-sig`, cela donne un JSON invalide et une seule ligne ignorée : l'analyste croit à une absence d'événements. Correction : « BOM UTF-16 détecté → décodage UTF-16 ».
- `Get-WinEvent | ConvertTo-Json` en PS 5.1 sérialise `TimeCreated` en `"/Date(…)/"` et ne produit pas d'objet `Data`. L'hypothèse « format normalisé » suppose un script d'export : C6b doit le fournir dans le README (`[xml]$_.ToXml()` vers `Data`, `TimeCreated.ToString("o")`).
- 7 décimales (.NET `"o"`) : vérifié, `datetime.fromisoformat` et pydantic les acceptent en Python 3.12 (troncature à la microseconde). `Z` est accepté.

### M4. Prompt et budget de contexte

10 preuves × un `Message` Windows français (environ 1,5 ko pour un 4624) dépassent `ctx = 4096`. Les messages multilignes cassent le format « une ligne par preuve ». Enfin, `max_tokens = 700` ne suffit pas pour 4 rubriques de 1 500 caractères : JSON tronqué, `SortieInvalide`, repli systématique avec le vrai SLM. Correction (§21, Prompt) : « chaque preuve = `horodatage.isoformat(timespec="seconds") hote ` + `" ".join(message.split())[:300]` ». Prévoir aussi `longueur_max_recit = 800`, ou un `max_tokens` incident dédié, à confirmer en V-série.

### M5. Tri et égalités

- Détections : départage ajouté en K3.
- `Detection.hotes` : `sorted(set(...))`, ordre précisé en K3.
- Tri des événements : `fichier` comparé en `casefold`, cohérent avec E2.
- Deux exécutions identiques : comparer `incident.json` en excluant `id_lot` et les durées. Les nommer dans le test C5.

### M6. Critères qu'un test ne peut pas trancher

| Critère | Problème | Reformulation testable |
|---|---|---|
| « en quelques minutes » (Success signal) | Non mesurable en CI, le faux moteur répond instantanément | Le test e2e de démo avec le faux moteur dure < 30 s ; la durée réelle est mesurée par le banc (hors CI) |
| « au moins 60 % de lignes bénignes réalistes » | « réalistes » est subjectif ; « lignes » mélange les fichiers | Ratio de K4, testé par C5 |
| « jeu de démonstration entièrement lu » et « lignes illisibles comptées » | Contradiction apparente | `ignorees` de la démo = liste exacte de `attendu.yaml` |
| « récit tiré des preuves » | Non vérifiable avec le faux moteur | Vérifier seulement que le prompt contient les `max_preuves` premières preuves |
| « textes types rédigés en propre » | Non testable | Revue humaine ; test : aucune URL hors attack.mitre.org |
| « ne jamais affaiblir le test » (C5) | Contournable en modifiant `attendu.yaml` | Règle de K4 |
| CAP-7 « code 3 seulement s'il y a au moins une détection » | Dépend de K6 | Deux tests : dossier sans détection + moteur injoignable → 0 ; démo + injoignable → 3 |

### M7. `CatalogueReglesYaml` : format et erreurs

Fixer :
- format : chaque `donnees/regles/*.yaml` est une **liste** de règles, fichiers lus triés ;
- validation : `Regle.model_validate`, puis `verifier_regles` ; toute erreur lève `ConfigurationInvalide` (code 2), toutes les erreurs listées ;
- chargement au constructeur ;
- URL ATT&CK : `^https://attack\.mitre\.org/techniques/T\d{4}(/\d{3})?/$`, cohérente avec l'`id` (`T1110.001` → `/T1110/001/`) ;
- `source` égale au préfixe de l'`id` ;
- aucune commande `waveaudit regles verifier` n'est exigée : le dire, pour que C6 n'en invente pas.

### M8. Pièges Windows à nommer dans les `invoke_dev_with`

- `open(..., newline="")` pour le CSV (sinon `\r` est doublé dans les champs multilignes).
- `$` en regex ne s'arrête pas avant `\r` : retirer `\r` à la lecture. `.gitattributes` force déjà LF dans le dépôt, mais pas dans les journaux de l'analyste.
- Correspondance de noms de fichiers en `casefold`, sans `glob`, sensible à la casse selon la version.
- `-o` vers un .docx ouvert dans Word donne `PermissionError` : code 4, comme pour `fiches`.
- `--annee` par défaut à l'année courante : aucun test ne doit en dépendre (toujours `annee=2026`).
- `Path.name` seulement dans `origines`, jamais de chemin absolu (AD-8).

---

## Ce que C1 doit absolument créer (C2, C3 et C4 ne touchent jamais au socle)

1. `domaine/incident.py` : toutes les formes de §21 avec les validations de E8, `Recit.regle_titre`, `Condition.au_moins_un`, `PortsIncident` revu (K6, dans `ports.py`), `schema_recit`, et les constantes `CHAMPS_WINDOWS`, `CHAMPS_LINUX`, `PROGRAMMES_LINUX = {"sshd","sudo","useradd"}`, `SEVERITES = ("critique","elevee","moyenne","faible")`, `TYPES_INDICATEUR`, `MOTIF_TECHNIQUE`, `MOTIF_IPV4`, `MOTIF_HACHAGE`. Les imports `Reference`, `Motif`, `Statut` et `CodeMotif` depuis `domaine.modeles` sont permis par AD-1 (`domaine` vers `domaine`) et par `test_architecture`. `RapportIncident`, `RequeteIncident` et `ResultatIncident` dans `domaine` suivent le précédent de `RequeteLot` : compatibles.
2. `domaine/modeles.py` : `CodeMotif.INDICATEUR_RETIRE = "indicateur_retire"` et rien d'autre. `Motif.code: CodeMotif` l'accepte. Vérifier qu'aucun test du socle n'énumère `CodeMotif` (c'est le cas : `test_modeles.py` ne le fait pas).
3. `domaine/ports.py` : `SourceJournaux`, `CatalogueRegles`, `ExporteurIncident`, `PortsIncident` (forme K6).
4. `domaine/configuration.py`, `config/waveaudit.toml` : `ConfigChemins.regles` et `ConfigIncident` (E1). `config_test` n'a alors pas à changer, car `[chemins]` y est déjà absolutisé.
5. `tests/faux_moteur.py` : mode `<regle>` et `REFERENCES_INVENTEES_INCIDENT` (K7), `SCENARIOS` inchangé.
6. **`tests/donnees/incident/canoniques.yaml`** (la pièce maîtresse) : pour chacune des 17 lignes d'attaque de E6 et pour au moins 8 voisines bénignes, `{format: json|csv|syslog, brut: <ligne ou objet>, evenement: <Evenement attendu sans fichier ni ligne>, regles: [ids déclenchés, possiblement vide]}`. C2 vérifie `lire(brut) == evenement`. C3 vérifie que `detecter` sur `evenement` déclenche exactement `regles` (en agrégation, en dupliquant l'événement à des horodatages construits). C4 y prend ses `Hashes` et ses messages.
7. `tests/incident_outils.py` : `evenement(**surcharges) -> Evenement` et `regle(**surcharges) -> Regle`, valides par défaut, pour que C3 et C4 construisent leurs données de test de la même façon.
8. `donnees/regles/.gitkeep`, `donnees/demo/incident/.gitkeep`.
9. Tests : `test_incident_modeles.py` (chaque validation de E8, `schema_recit`), `test_config` (section `incident` et `chemins.regles`), `test_faux_moteur` (nominal incident, `references_inventees` incident, sans balise), `test_architecture` inchangé et vert.

## `invoke_dev_with` : ajouts à coller

- **C1** : « Appliquer contrats §21 révisé (revue adversariale K1-K7, E1, E8). Créer en plus `tests/donnees/incident/canoniques.yaml` et `tests/incident_outils.py` (liste « Ce que C1 doit créer »). Ne pas modifier `application/config.py` : le chemin des règles est dans `[chemins]`. »
- **C2** : « Champs exactement selon formats-incident.md "Champs normalisés" ; test paramétré : chaque entrée `canoniques.yaml` est lue à l'identique. Fichiers de démo : `security.json`, `system.json`, `sysmon.csv`, `auth.log`, `syslog`. Lignes d'attaque exactement celles de la chronologie normative, entourées de bénin respectant la liste des lignes interdites. `attendu.yaml` selon le schéma figé, calculé à la main avec l'algorithme d'agrégation et les règles d'indicateurs de §21. Ne jamais utiliser 203.0.113.254 ni 0f0f…. »
- **C3** : « Conditions et agrégations recopiées de la table normative. `verifier_regles` rejette les clés hors `CHAMPS_<source>`, les conditions vides et les textes types contenant un jeton ATT&CK, IP ou hachage. Les vecteurs d'agrégation de §21 sont des tests. `detection.py` laisse `indicateurs=[]` et n'importe pas `domaine.indicateurs`. Test paramétré sur `canoniques.yaml`. »
- **C4** : « Sources, exclusions, `Hashes`, IPv4 mappée et `origines` selon §21 révisé ; motifs importés de `domaine.incident`. Garde-fous : ordre et motifs de §21 ; `titre` complété seulement s'il est vide ; test du jeton horaire `08:02:10` conservé. »
- **C5** : « `creer_ports_incident` + `ouvrir_moteur_incident` (K6) ; `assembler_rapport` (E5) ; extraction de l'écrivain de journal de `lot.py` (E7) ; comparaison à `attendu.yaml` selon K4, ratio bénin >= 0,60, `annee=2026`. »
- **C6a** (parallèle à C2-C4) : « `export_incident_docx.py` sur un `RapportIncident` construit en mémoire ; mise en forme de E5 ; bandeau d'`export_docx`. » **C6b** (après C5) : CLI, `test_hors_ligne`, README (script d'export PowerShell, limite heure d'été).
