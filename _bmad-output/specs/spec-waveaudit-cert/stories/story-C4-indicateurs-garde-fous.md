---
id: C4
title: Indicateurs de compromission et garde-fous du récit
status: review
sources:
  - ../stories.yaml
  - ../SPEC.md
  - ../formats-incident.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
  - ./story-C1-socle-cert.md
---

# Story C4 — Indicateurs de compromission et garde-fous du récit

## Décision d'orchestration (point final des motifs normatifs)

Report consigné par C1 (`story-C1-socle-cert.md`, section Reports) : `MOTIF_TECHNIQUE`,
`MOTIF_IPV4` et `MOTIF_IPV6` (`domaine/incident.py`, non modifiés, comportement figé par
`test_motifs_point_final_comportement_fige`) ratent un jeton suivi d'un point final de
phrase (« T1110.001. », « 203.0.113.254. », « 2001:db8::1. »). C4 applique ces motifs sur une
**copie** du texte, de même longueur, où chaque « . » suivi d'un blanc ou de la fin du texte
est remplacé par une espace (`_copie_sans_point_final`, `garde_fous_incident.py`) ; les
positions des jetons trouvés sur la copie restent valables pour le retrait dans le texte
d'origine (longueur inchangée). Les trois cas (technique, IPv4, IPv6 inventés en fin de
phrase) sont testés et retirés.

## Livré

- `src/waveaudit/domaine/indicateurs.py` (nouveau) : `extraire(evenements) -> list[Indicateur]`
  (CAP-4). Sources, normalisation et exclusions : table de `formats-incident.md` ; IPv4 de
  `message` par `MOTIF_IPV4` puis `ipaddress.ip_address` ; IPv4 mappée → IPv4 ; comptes
  exclus (vide, `-`, `SYSTEM`, `LOCAL SERVICE`, `NETWORK SERVICE`, `ANONYMOUS LOGON`, finissant
  par `$`), `TargetUserName` ignoré pour les `event_id` 4728/4732/4756 ; hachages MD5 (32),
  SHA1 (40), SHA256 (64 hex), IMPHASH ignoré ; origines `fichier:ligne` triées ; résultat trié
  `(type, valeur)`. N'importe pas `domaine.detection`.
- `src/waveaudit/domaine/garde_fous_incident.py` (nouveau) : `appliquer_recit(sortie_brute,
  regle, detection, longueur_max, motifs_initiaux=())` (CAP-5), dans l'ordre de §21 : jetons
  `MOTIF_TECHNIQUE` gardés ssi égalité exacte avec une référence de la règle
  (`reference_retiree` sinon), `MOTIF_IPV6` puis `MOTIF_IPV4` (IPv4 incluse dans une IPv6
  valide non retraitée) puis `MOTIF_HACHAGE` gardés ssi présents dans
  `detection.indicateurs`, candidat non valide pour `ipaddress` laissé tel quel
  (`indicateur_retire` sinon), nettoyage des espaces et parenthèses/crochets vides, rubrique
  `recit`/`impact`/`recommandation` < 20 caractères complétée par le texte type de la règle
  (`rubrique_completee`), `titre` recopié depuis `regle.titre` seulement s'il est vide
  (même code), troncature à `longueur_max`, `regle_titre = regle.titre` toujours,
  `statut = a_revoir` ssi `motifs` non vide.
- `tests/unitaires/test_indicateurs.py` (10 tests) et `test_garde_fous_incident.py`
  (14 tests), construits sur `tests/incident_outils.py` (fabriques `evenement`, `regle`,
  `detection`) ; aucune modification de `domaine/incident.py`, `domaine/modeles.py` ni des
  fixtures de C1.

## Écarts au contrat

Aucun.

## Reports

Aucun.

## Revue

- info — dev — vérifié : le vecteur `REFERENCES_INVENTEES_INCIDENT` du faux moteur
  (`" T9999 T1110.999 203.0.113.254 " + "0f"*32`) ne percute pas lui-même le point final
  (jetons suivis d'espaces, sauf le dernier hachage qui n'est pas affecté par le lookahead) ;
  les cas de point final collé à un jeton sont couverts par des tests dédiés
  (`test_technique_inventee_point_final_seule_retiree`,
  `test_ipv4_inventee_point_final_retiree`, `test_ipv6_inventee_point_final_retiree`).
- Complexité : O(n log n) par rubrique (tri des décisions de retrait, bornée par la longueur
  du texte généré, `longueur_max` ≤ quelques centaines de caractères) ; `extraire` : O(n log n)
  dans le nombre d'événements (tri initial puis un passage).
- medium — second avis — corrigé : la neutralisation ne couvrait que « . » suivi d'un blanc
  ou de la fin ; « (203.0.113.254.) », « 203.0.113.254., », « 2001:db8::1.) », « (T1059.003.) »,
  « 203.0.113.254... » laissaient passer le jeton inventé (prouvé). `_POINT_FINAL` couvre
  désormais une suite de « . » suivie d'un blanc, de la fin ou de `) ] } > » " ' ” ’ , ; : ! ?`,
  remplacée par autant d'espaces (longueur conservée). Un « . » suivi d'un chiffre n'est jamais
  touché. Tests : `test_jeton_invente_point_puis_ponctuation_retire` (9 cas),
  `test_non_mutilation_point_puis_ponctuation` (versions, horodatages, `T1110.001`, IP connue et
  IPv4 mappée suivies de « .) », « ., », « .; »).
- low — second avis — rejeté (conforme à §21) : un candidat IPv6 de prose valide pour
  `ipaddress` (« A::B », « cafe::dead », « :: » isolé) est retiré comme `indicateur_retire`.
  C'est la lettre de §21, étape 3 ; à changer seulement par une révision du contrat.
- low — second avis — reporté (hors contrat) : fragments résiduels après retrait
  (« Source (.) », « vers :443 », « /24 », « « . » »). §21, étape 4, ne prévoit que la réduction
  des espaces et la suppression de `()` et `[]` vides ; retirer le port, le préfixe ou la
  ponctuation orpheline demande une révision de §21 (récit marqué `a_revoir` dans tous ces cas).
- low — reviewer — corrigé : le test redéfinissait `REFERENCES_INVENTEES_INCIDENT` au lieu de
  l'importer de `tests/faux_moteur.py` (dérive silencieuse possible) ; importé.
- low — reviewer — corrigé : le cahier demandait des données de test tirées de
  `canoniques.yaml` (Hashes, messages), absentes ; ajout de
  `test_extraire_entrees_canoniques_oracle_a_la_main` (chrono-01, chrono-10, chrono-14, attendu
  écrit à la main, origines comprises). `test_extraire_resultat_trie_type_puis_valeur` reste
  tautologique (trie sa propre sortie) ; le nouveau test fixe l'ordre attendu.
- info — reviewer — vérifié : `extraire` et `appliquer_recit` ne sont appelés nulle part hors
  tests (branchement prévu par C5) ; `domaine.detection` non importé ; aucun fichier du socle
  ni du MVP modifié.
- Complexité : 0 constat (rubriques bornées par `longueur_max`, test d'inclusion IPv4/IPv6
  quadratique sur quelques jetons ; `extraire` en O(n log n)).
