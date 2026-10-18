---
id: M1
title: Verrou unique et moteur à la demande
status: review
sources:
  - ../stories.yaml
  - ../SPEC.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/impacts-v2.md
---

# Story M1 — Verrou unique et moteur à la demande

## Livré

- `application/moteur_demande.py` (nouveau, contrats §24, AD-11, AD-20) :
  - `Occupation` (dataclass figée : `nature`, `id_lot`, `index`, `debut`) ;
  - `VerrouUnique` : `prendre` non bloquant (False si pris), `definir` (remplace
    l'occupation provisoire, `RuntimeError` si le verrou n'est pas pris), `liberer`,
    `occupation()` (copie, sous verrou interne) ;
  - `MoteurALaDemande(config)` : `inactivite_s = config.ui.inactivite_moteur_s` ;
    `utiliser(modele)` réutilise le moteur ouvert pour le même **nom résolu**
    (`choisir_modele(...).nom` en local-gere, choix défaut/repli figé au premier usage ;
    `modele or modele_api` en externe), sinon ferme l'ancien puis passe par
    `composition.ouvrir` et `sonder()` ; un échec referme et remonte. Verrou interne et
    compteur d'usages : l'entrée annule la minuterie ; en sortie du dernier usage, une
    `threading.Timer` daemon est armée ; l'échéance ne ferme que si aucun usage n'est en
    cours et que la minuterie est encore la courante. `fermer()` idempotent.
- `composition.py` inchangé.
- `tests/unitaires/test_moteur_demande.py` (nouveau) : prise non bloquante, occupation copiée,
  `definir`, réutilisation, changement de modèle (fermeture avant ouverture), échec
  d'ouverture (sonde injoignable, modèle inconnu), arrêt après 0,1 s, minuterie réarmée,
  `fermer` idempotent, clé = nom résolu, concurrence (minuterie 0,01 s, deux fils), mode
  externe sans processus. `_FauxServeur` et `_installer` importés de `test_composition.py`
  (sous-classe locale pour pointer vers le faux moteur), sans le modifier.

## Reports

- Intégration web (création par `creer_app`, 409 `lot_en_cours`, `fermer()` avant un lot ou
  un incident, attente de 10 s au lifespan) : W2.
- `utiliser` suppose l'appel sous `VerrouUnique` : un changement de modèle pendant un usage
  concurrent n'est pas refusé (hors contrat).
