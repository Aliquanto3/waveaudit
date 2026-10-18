# Bilan des modèles (story V2)

Mesures du 2026-10-18 sur le poste de développement : i5-1145G7, 4 cœurs physiques et 8 logiques, 15,7 Gio de RAM, Windows 11. Ce n'est pas l'EliteBook cible.
llama-server b11714 en CPU, `threads = 4`, `ctx = 4096`. Configuration livrée : `temperature = 0.2`, `seed = 42`, `max_tokens = 700`.

## Protocole

- Commande : `uv run waveaudit banc var/banc-sous-ensemble --modele <nom>`. Les modèles sont lus dans le `var/` du dépôt principal, par un `waveaudit.local.toml` ignoré par git. Aucun téléchargement.
- Les 6 notes, copiées de `donnees/demo/notes/` :
  - classiques : `01-xss-reflechi`, `11-kerberoasting`, `16-tls-obsolete` ;
  - difficiles : `22-chemin-bloodhound-court`, `26-partage-trouve-en-scannant`, `29-erreur-etrange-generateur-devis`.
- Un seul llama-server à la fois. Après chaque run, psutil ne trouvait aucun llama-server restant. Chaque run a duré moins de 10 min (le plus long : 2 min 10 s).
- Garde réseau actif : la commande `banc` n'a pas été modifiée.
- Indicateur ajouté pour ce bilan : la « recopie ». C'est la similarité `difflib.SequenceMatcher` (de 0 à 1) entre chaque rubrique de la fiche et la même rubrique du constat type retenu, en moyenne sur les 4 rubriques et les 6 fiches. 1 veut dire recopie mot pour mot. Le script de mesure est hors dépôt.

## Banc des 4 modèles (prompt et réglages livrés)

| Modèle | Rôle | Médiane / max par fiche | Lot total | Pic RSS app / moteur / total | Fiches ok | top1 / top3 | Recopie |
|---|---|---|---|---|---|---|---|
| granite-4.0-1b-q4km | défaut | 17,1 s / 22,4 s | 111 s | 74 / 2 408 / 2 475 Mio | 6/6 | 4/6 / 6/6 | 0,93 |
| minicpm5-1b-q4km | repli | 12,9 s / 22,3 s | 83 s | 71 / 1 193 / 1 258 Mio | 6/6 | 4/6 / 6/6 | 0,83 |
| qwen3-1.7b-q4km | candidat | 20,4 s / 23,1 s | 129 s | 71 / 2 719 / 2 789 Mio | 6/6 | 4/6 / 6/6 | 0,76 |
| qwen3.5-0.8b-q4km | candidat | 11,4 s / 12,7 s | 73 s | 71 / 1 274 / 1 338 Mio | 6/6 | 4/6 / 6/6 | 0,82 |

- Le « lot total » est mesuré autour de la commande : démarrage d'`uv` et de llama-server compris.
- top1 et top3 ne dépendent pas du modèle : c'est la recherche BM25. Les notes 01 et 29 ont le bon constat en 2e ou 3e position seulement.

### Appréciation qualitative par modèle

- **granite-4.0-1b (défaut)** : JSON toujours conforme et français correct, mais presque aucune adaptation. Titre, impact et recommandation sont recopiés du catalogue, la description à 89 %. Seule la note 29 est réécrite d'après la note. Faute « Élégation » (note 22).
- **minicpm5-1b (repli)** : rapide et léger, mais pas fiable. Note 26 : la description répète « sans restriction d'accès » jusqu'à la longueur maximale, puis finit sur un caractère japonais, avec le statut `ok`. Note 29 : description incohérente (« améliore la préparation des attaques »). Note 26 : titre « Avis : … ».
- **qwen3-1.7b (candidat)** : c'est lui qui adapte le mieux. La note 22 reprend `compte-svc-sauvegarde`, la GPO et l'OU Finance sans invention, et la note 29 reprend les faits de la trace. Une faute de sens dans la note 01 (« complicité de compte »). C'est aussi le plus lourd et le plus lent.
- **qwen3.5-0.8b (candidat)** : rapide, léger, adaptation partielle (notes 16 et 29). Note 29 : l'impact recopie une phrase de la note, qui n'est pas un impact, et la recommandation est hors sujet (« validation stricte sur les types »).

## Relecture des 6 fiches du modèle par défaut (réglages retenus)

Lot `20261018-015936`, granite-4.0-1b, prompt livré.

| Note | Constat retenu | Fidélité à la note | Invention | Appréciation |
|---|---|---|---|---|
| 01 XSS réfléchi | WEB-XSS-STOCKE (attendu : réfléchi, en 2e position) | Non : la fiche décrit une donnée « enregistrée puis restituée à d'autres visiteurs », ce que la note ne dit pas | Oui, par le choix du constat : persistance et attaque « à grande échelle » | à refaire (choisir le 2e candidat) |
| 11 Kerberoasting | AD-KERBEROASTING | Juste mais générique : aucun des faits (une dizaine de tickets, deux comptes cassés, groupe des opérateurs de sauvegarde) | Non | retouches légères |
| 16 TLS obsolète | CRYPTO-TLS-OBSOLETE | Juste mais générique : le repli forcé observé n'est pas cité | « voire SSL » n'est pas observé | retouches légères |
| 22 Chemin BloodHound | AD-ACL-DANGEREUSE | Juste mais générique : ni le compte, ni la GPO, ni l'OU | Non ; faute « Élégation » | retouches légères |
| 26 Export NFS | INFRA-NFS-EXPORTE | Juste mais générique : ni l'export `*` ni les documents RH | Fait non vérifié : `no_root_squash` est donné comme « parfois » présent, alors que la note n'a pas regardé les options | retouches légères |
| 29 Erreur de gabarit | WEB-DIVULGATION-ERREURS (attendu : SSTI, en 3e position) | Description fidèle à l'erreur 500, mais elle passe à côté de l'évaluation du champ, qui est le vrai constat | Recommandation en partie confuse (« ne pas évaluer les expressions arithmétiques… avant d'être insérés ») et une phrase de remplissage | à refaire (choisir le 3e candidat) |

Bilan : 0 utilisable tel quel, 4 retouches légères, 2 à refaire. Aucune fiche n'invente d'identifiant ni de référence.

- **Points signalés par V1.**
  - Rubriques trop proches du catalogue : confirmé (recopie de 0,93). C'est le défaut principal du modèle par défaut.
  - Note 01 rattachée à WEB-XSS-STOCKE : confirmé, avec les 4 modèles. C'est la recherche, pas le prompt. La note 29 a le même défaut (WEB-SSTI en 3e position).
  - Le prompt ne peut pas corriger le rattachement : le constat est choisi avant l'appel au modèle. Ce point est reporté hors de V2 (voir Reports).

## Réglage du prompt sur le modèle par défaut (3 itérations)

Seule la consigne système (`CONSIGNE` de `workflows/fiches/prompt.py`) a varié. L'ordre `<constat>` puis `<note>` est figé par le contrat §8. `temperature` et `max_tokens` sont restés aux valeurs livrées.

| Essai | Changement | Fiches ok | Motifs | Médiane / max | Recopie (description) | Défauts relevés |
|---|---|---|---|---|---|---|
| Base | prompt livré | 6/6 | aucun | 17,1 s / 22,4 s | 0,93 (0,89) | recopie du catalogue |
| 1 | constat type présenté comme un modèle générique, consigne par rubrique (faits précis de la note, « ne recopie pas »), titre « court » | 5/6 | 1 `rubrique_completee` (titre de la note 26 sous 20 caractères) | 27,1 s / 43,6 s | 0,73 (0,35) | recommandation de la note 11 gonflée de mesures générales (RBAC, correctifs) ; « ont été casser » |
| 2 | essai 1, plus longueur en phrases par rubrique, « aucune mesure générale », « ne présente pas comme constaté ce que la note n'a pas vérifié » | 6/6 | aucun | 22,0 s / 53,6 s | 0,79 (0,56) | boucle de répétition dans la recommandation de la note 22 (tronquée à 1 200 caractères) ; recommandation de la note 29 inversée (« ne pas journaliser ») ; description de la note 22 fausse (« lien direct avec le groupe des admins du domaine ») |
| 3 | essai 1 sans « court » pour le titre, plus « ne présente pas comme constaté… » | 6/6 | aucun | 33,9 s / 49,2 s | 0,74 (0,43) | boucle de répétition dans la recommandation de la note 01 ; même erreur sur la note 22 |

Contrôle hors itération : la consigne de l'essai 3 sur qwen3-1.7b donne une recopie de 0,39, sans boucle, avec une adaptation réelle des 6 fiches. Mais 4/6 fiches ok seulement : 2 `reference_retiree`, car le modèle cite l'URL de l'actif, qui vient pourtant de la note. Médiane 36,1 s, max 38,8 s, pic total 2 948 Mio. Il reste des erreurs de sens (« Groupe de préférence d'organisation », « domaine LOCAL »).

### Réglages retenus

**Aucun.** Le prompt, `temperature = 0.2` et `max_tokens = 700` restent ceux livrés.

- Aucun essai n'améliore les mesures de la story : le taux ok est égal ou plus bas, et la durée médiane passe de 17 s à 22-34 s.
- Le gain d'adaptation (recopie de la description de 0,89 à 0,35-0,56) se paie en boucles de répétition et en erreurs de sens. Avec le prompt livré, granite n'en produit pas.
- Les boucles appellent une pénalité de répétition (`repeat_penalty`, côté `moteur_openai` et `[moteur]`), hors du périmètre de V2. Baisser `max_tokens` ne les supprimerait pas : la sortie serait tronquée, donc du JSON invalide, puis un repli.
- `temperature` n'a pas été mesurée seule : les 3 itérations ont servi à la consigne, le levier principal du défaut de recopie.

## Recommandation pour l'EliteBook

- Ne pas changer les rôles dans V2. La qualité d'adaptation recommande **qwen3-1.7b** comme défaut, s'il tient en mémoire et en durée sur l'EliteBook. Ici, il demande environ 2,8 Gio de RSS au total et 20 s par fiche avec le prompt livré, 36 s avec un prompt d'adaptation.
- Pour l'adopter, il faut d'abord :
  1. ne plus retirer l'URL de l'actif quand elle vient de la note (garde-fou §6) ;
  2. adopter la consigne de l'essai 3 ;
  3. refaire ce banc sur l'EliteBook.
- granite-4.0-1b reste le choix sûr : JSON stable, pas de boucle, 17 s par fiche. Mais ses fiches demandent toujours d'y reporter les faits de la note.
- **MiniCPM5 en repli : à surveiller.** Il est rapide (13 s, 1,2 Gio) mais a produit une fiche dégénérée marquée `ok` et un récit d'incident en anglais (voir plus bas). qwen3.5-0.8b est une alternative de repli aussi légère (11 s, 1,3 Gio), sans dégénérescence sur ce banc.
- Avant de conclure, remesurer sur l'EliteBook : la RAM disponible y décide du choix entre défaut et repli (`ram_min_defaut_go = 4.5`).

## Workflow incident (démo CERT, sans modification)

Commande : `uv run waveaudit incident donnees/demo/incident --modele <nom>`. Psutil ne trouvait aucun llama-server restant après chaque run.

| Modèle | Récits ok | Durée par récit | Lot total | Remarques |
|---|---|---|---|---|
| granite-4.0-1b-q4km (défaut) | 16/16, 0 à revoir | 8 à 22 s | 210 s | récits en français, factuels (hôte, IP, plage horaire, ports) |
| minicpm5-1b-q4km (repli) | 16/16, 0 à revoir | 4 à 8 s | 88 s | JSON valide avec `reflexion = false` ; 1 récit sur 16 en anglais, et faux sur le sens (« Bastion01 has attempted to brute-force »), avec le statut `ok` |

## Reports (hors périmètre V2)

- **Rattachement** des notes 01 (réfléchi contre stocké) et 29 (SSTI contre divulgation d'erreurs). À traiter par la recherche ou par les mots du catalogue, dans une story de calibrage.
- **Garde-fous fiches** :
  - une sortie dégénérée (répétition jusqu'à `longueur_max_rubrique`) reste `ok` ;
  - l'URL de l'actif citée depuis la note est retirée comme une référence inventée ;
  - le seuil de 20 caractères vaut aussi pour le titre, et pénalise un titre court mais juste.
- **Pénalité de répétition** : paramètre `repeat_penalty` à exposer dans `[moteur]` et dans `moteur_openai`, puis à remesurer avec la consigne de l'essai 3.
- **Langue des récits d'incident** avec MiniCPM5 : à contrôler (consigne ou garde-fou de langue), dans une story CERT.

## Consigne de l'essai 3 (non retenue, pour reprise)

```
Tu es un assistant de rédaction d'audit de sécurité. Le constat type fourni entre les balises <constat> est un modèle générique. Adapte-le aux observations de la note d'audit fournie entre les balises <note> : rédige en français professionnel la fiche de ce cas précis, avec les rubriques titre, description, impact et recommandation.
- titre : il nomme la vulnérabilité et, si la note le donne, l'actif touché.
- description : ce que l'auditeur a constaté (actif, test mené, résultat obtenu), avec les faits précis de la note ; ne recopie pas la description générique.
- impact : les conséquences pour ce cas, d'après la note.
- recommandation : les actions qui corrigent ce cas, en t'appuyant sur le constat type.
- N'invente aucun identifiant, aucune référence, aucune URL ni aucun fait absent de la note ; ne présente pas comme constaté ce que la note n'a pas vérifié.
- Garde le vecteur CVSS par défaut du constat type, sauf si la note le contredit.
- Réponds uniquement par un objet JSON conforme au schéma demandé.
```

Lots bruts : `var/sorties/` du dépôt principal. Base : `20261018-015936`, `-020204`, `-020327`, `-020537`. Essais : `-020813`, `-021127`, `-021441`. Contrôle qwen3 : `-021834`. Incident : `-022232`, `-022603`.
