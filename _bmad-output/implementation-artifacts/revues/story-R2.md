# Revue — story R2 (persistance de la relecture et lot.json)

Commit relu : 8c57703 (base c7a9743), branche `story/R2`. Non rebasée (B1 en parallèle sur
`banc.py`, `cli.py`, `composition.py` : fichiers disjoints de R2).
Verdict : conforme à §25 « Persistance » et §30 (`lot.json`) ; deux défauts moyens corrigés.

| Sévérité | Source | Constat | Décision |
|---|---|---|---|
| moyenne | second avis 1 | `demarrer_regeneration(..., occupation=)` : la route prend le `VerrouUnique` `(regeneration, id, index)` avant l'appel (§26). Passer cette occupation (appel naturel) faisait lire une entrée interrompue comme `en_cours` réelle : refus `generation_en_cours` à chaque essai, entrée jamais relançable. Passer `None` était juste mais reposait sur une consigne. | Corrigé : paramètre retiré (signature du §25), lecture toujours sans occupation ; `generation_en_cours` reste dans l'ordre des refus, tenu en pratique par le verrou (409 `lot_en_cours`). Test d'ordre réaligné. |
| moyenne | second avis 3 | `id_lot` fourni d'un lot déjà exécuté : `verifier_id_lot` accepte le dossier existant, `initialiser` écrasait `relecture.json` (corrections et validations perdues). Inatteignable aujourd'hui (seule la route fournit un id, neuf), mais contraire à §25 « Relance ». | Corrigé : `executer_lot` lève `EntreeInvalide("lot déjà exécuté")` si `relecture.json` ou `journal.jsonl` existe, avant le journal. `lot.json` seul (écrit par la route) reste accepté. Test `test_id_lot_deja_execute_refuse`. |
| moyenne → faible | second avis 2 | Verrous `threading` et provisoire au nom fixe partagés entre processus. | Rejeté : SPEC (l. 87) et §26 excluent toute écriture de l'UI sur un lot vivant d'un autre processus (409 `lot_en_cours_externe` sur correction, validation, candidat) ; le nom `.relecture.json.partiel` est fixé par §30. À tenir par W3a (consigne ci-dessous). |
| faible | second avis 4 | `relecture.json` illisible ou `version_schema != 1` : `ValidationError` (sous-classe de `ValueError`), pas `RefusRelecture`. | Reporté (écart à arbitrer) : aucun code d'API prévu au §26 ; nos écritures atomiques ne produisent pas ce cas. W3a : ne pas laisser un 500 brut. |
| faible | second avis 5 | Pas de `fsync` avant `os.replace`. | Rejeté : non exigé par §25 ; perte limitée à la dernière écriture en cas de coupure d'alimentation (POC). |
| faible | second avis 6 | `unlink` du provisoire dans le `finally` pouvait masquer l'erreur d'origine. | Corrigé : `OSError` de suppression journalisée, l'erreur d'origine remonte. Test `test_provisoire_non_supprime_ne_masque_pas_l_erreur`. |
| faible | second avis 7 | État vide lu depuis un `lot.json` à `langue=None` → `"fr"`. | Laissé : seulement avant `initialiser` (aucune entrée). Consigne W2 : la route écrit la langue résolue. |
| faible | second avis 8 | `pid` de `lot.json` jamais lu. | Rejeté : lecture par `lots.py` (W2, §30 [revue A13/E12]). |
| faible | second avis 9 | `ecrire_fiche_lot` : test d'existence puis écriture sans verrou. | Rejeté : écrivains séquentiels (route puis fil du lot, même processus). |
| — | reviewer | Complexité : 1 constat. `enregistrer_resultat` relit et réécrit tout `relecture.json` à chaque fiche (O(n²) par lot, inhérent au fichier unique du §25). Mesuré : 2,9 ms/fiche à 30 notes, 18 ms/fiche à 300 notes (1,4 Mio). | Laissé : négligeable devant 30 à 60 s de génération par fiche. |

Vérifié conforme : `.partiel` puis `os.replace` 10 × 100 ms, `lot_echoue` avec message dédié ;
aucune écriture en lecture (`charger`, repli `fiches.json`, génération interrompue) ; seule
l'entrée visée présentée dans `modifier` ; ordre des refus ; `regenerer` sur le modèle résolu,
langue du lot, `repli_moteur` → `echec` fiche gardée, toute exception → `echec` ; pas d'import
de `lot.py`/`moteur_demande.py` au niveau module ; `lot.json` incident (`langue=None`).

## Interfaces et consignes pour la suite

- **W3a (routes de relecture)** :
  - candidat : `prendre(Occupation("regeneration", id, index))`, puis
    `relecture.demarrer_regeneration(dossier, index, version, constat_id, confirmer,
    ids_catalogue=<ids du catalogue>)` (sans occupation), puis fil `relecture.regenerer(config,
    dossier, index, constat_id, moteur)` et `liberer()` dans son `finally` ; tout refus libère
    aussitôt ; refuser 422 `modele_indisponible` avant (§24).
  - correction / validation : `relecture.modifier(dossier, index, version, regle,
    occupation=verrou.occupation())` ; GET : `relecture.charger(dossier,
    occupation=verrou.occupation())`.
  - refuser toute écriture (409 `lot_en_cours_externe`) quand `lots.py` voit le lot vivant
    dans un autre processus : c'est ce qui rend sûrs les verrous `threading` de R2.
  - `OSError` (dont `PermissionError`) d'écriture → 503 `ecriture_impossible` ;
    `RefusRelecture.code` repris tel quel ; un `ValueError` de lecture (fichier corrompu) ne
    doit pas sortir en 500 brut (code à arbitrer).
- **W2 (accueil, `lots.py`)** : la route écrit `lot.ecrire_fiche_lot(dossier, id_lot=id,
  workflow=..., langue=<langue résolue : requête ou config.fiches.langue ; None pour un
  incident>, modele_demande=...)` avant le 303 ; `executer_lot` ne la réécrit pas. `lot.json`
  porte `pid` et `cree_le` (ISO avec fuseau) pour `processus_actif`. Lire l'état de relecture
  par `relecture.charger`, jamais en ouvrant `relecture.json` directement.
- **X2 (CLI `exporter`)** : `relecture.charger(dossier)` (repli v0.1.0 compris) ;
  `RefusRelecture("lot_inconnu")` si rien ; refuser un lot vivant d'après `lots.py`.

## Écarts à arbitrer

- Code d'erreur pour un `relecture.json` illisible (aujourd'hui `ValidationError`).
- §26 liste 409 `generation_en_cours` pour `POST …/candidat` ; avec l'ordre « verrou puis
  `demarrer_regeneration` » du même §26, une régénération en cours donne 409 `lot_en_cours`.

Tests : ciblés (relecture, lot, incident) 59 réussis ; suite complète 952 réussis,
2 désélectionnés ; `ruff check` et `ruff format --check` propres.
