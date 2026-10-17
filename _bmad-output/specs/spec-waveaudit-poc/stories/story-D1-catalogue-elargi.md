---
id: D1
title: Catalogue élargi et notes difficiles
status: review
sources:
  - ../stories.yaml
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
---

# Story D1 — Catalogue élargi et notes difficiles

## Livré

- `donnees/catalogue/{web,ad,infra,config,crypto,autre}.yaml` : 15 constats ajoutés (35 → 50),
  mêmes règles que la story 4 (6-12 mots-clés FR/EN génériques, titre ≥ 20 caractères, `source`
  au gabarit, références CWE/OWASP canoniques avec URL cohérente) :
  - web : `WEB-JWT-FAIBLE`, `WEB-CLICKJACKING`, `WEB-SSTI`, `WEB-GRAPHQL-INTROSPECTION`.
  - ad : `AD-ACL-DANGEREUSE`, `AD-ADCS-ESC1`, `AD-COMPTES-INACTIFS-PRIVILEGIES`.
  - infra : `INFRA-IPMI-EXPOSE`, `INFRA-NFS-EXPORTE`, `INFRA-SERVICE-GESTION-EXPOSE`.
  - config : `CONFIG-SAUVEGARDE-EXPOSEE`, `CONFIG-CORS-DEBUG`.
  - crypto : `CRYPTO-SECRET-DANS-LE-CODE`, `CRYPTO-CHIFFREMENT-FAIBLE-AU-REPOS`.
  - autre : `AUTRE-MFA-ABSENTE`.
  - Aucun des 35 constats figés (contrats §16) ni les mots-clés existants n'a été modifié.
- `donnees/demo/notes/21-*.md` à `30-*.md` : 10 notes de démonstration plus difficiles
  (formulations ambiguës, plusieurs vulnérabilités voisines évoquées puis écartées,
  sorties d'outils brutes — nmap, graphe AD façon BloodHound, scanner TLS, showmount,
  historique git, GraphQL introspection —, quelques fautes de frappe volontaires).
  Données fictives uniquement (`192.0.2.x`, `*.exemple.test`, `DOMAINE.LOCAL`), vocabulaire
  différent de celui du catalogue (§16), `constat_attendu` renseigné et existant (9 des 15
  nouveaux constats, plus `WEB-CLICKJACKING`/`WEB-SSTI` et un constat déjà figé
  `CRYPTO-CERTIFICAT-INVALIDE`), aucun doublon avec les notes 01-20 ni entre elles.
- `tests/unitaires/test_rattachement_demo.py` : scindé en deux tests. Le test historique
  (seuil CAP-3 inchangé : ≥ 18/20 top 3, ≥ 15/20 top 1) ne porte plus que sur les notes
  01-20 (filtrées par préfixe). Un nouveau test non bloquant mesure et affiche top1/top3 sur
  les notes 21-30 et appelle `pytest.xfail(...)` (non strict, par défaut du projet) si le
  top 3 est sous 7/10 ; mesuré : **top1 = 8/10, top3 = 10/10** (aucun xfail déclenché).
- `tests/unitaires/test_notes.py` : comptages et assertions réalignés sur 30 notes (au lieu de
  20) : validité, unicité et existence de `constat_attendu` (figé pour 01-20 strictement, figé
  ou nouveau pour l'ensemble des 30), couverture des familles minimales, absence de mention du
  constat/CWE, preuves fictives, nommage, rattachabilité (score BM25 max > 0).
- `tests/e2e/test_lot.py::test_lot_nominal_30_notes` (renommé) : comptages 20 → 30 (fiches +
  écartées, total du lot, nombre d'événements de fiche) réalignés sur le nouveau compte de
  notes de démonstration ; logique du test inchangée.
- `tests/donnees/notes/hors-sujet.md` : toujours à score 0 sur le catalogue élargi à 50
  constats (vérifié par `test_notes.py::test_note_hors_sujet_n_a_aucun_jeton_du_catalogue`).

## Écarts au contrat (variantes minimales)

- Aucun : ajouts seulement dans `donnees/catalogue` et `donnees/demo/notes`, et dans les tests
  qui en dépendent directement. `cli.py` et `application/banc.py` non touchés (story 15 en
  parallèle).

## Reports

- Deux des dix notes difficiles (`21-port-management-bizarre.md` rang 3,
  `29-erreur-etrange-generateur-devis.md` rang 2) ne sont pas en tête malgré un score global
  déjà au-dessus du seuil informatif (top3 = 10/10) ; pas d'action, le seuil CAP-3 ne porte que
  sur les notes 01-20 et la mesure sur 21-30 est volontairement non bloquante.

## Score consigné

30 notes de démonstration, catalogue réel (50 constats), réglages BM25 par défaut
(`k1=1.5`, `b=0.75`).

| Lot de notes | En premier | Top 3 | Seuil |
|---|---|---|---|
| 01-20 (inchangé, story 11) | 17/20 | 20/20 | ≥ 15/20, ≥ 18/20 (bloquant) |
| 21-30 (difficiles, D1) | 8/10 | 10/10 | ≥ 7/10 en top 3 (informatif, xfail non strict) |

Note hors sujet (`tests/donnees/notes/hors-sujet.md`) : score maximal 0,0 sur le catalogue à
50 constats.

Tests : ciblés `test_catalogue.py` (23), `test_notes.py` (31), `test_rattachement_demo.py` (2),
`test_lot.py` + `test_ui.py` + `test_cli.py` + `test_pipeline.py` (40) ; suite complète
252 verts, 1 déselectionné (`slow`) ; `ruff check` et `ruff format --check` verts ; contrôle
rapide vert.
