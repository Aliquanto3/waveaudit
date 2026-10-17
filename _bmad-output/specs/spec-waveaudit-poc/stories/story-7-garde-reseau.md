---
id: story-7
title: Garde réseau
status: review
sources:
  - ../stories.yaml
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/ARCHITECTURE-SPINE.md
---

# Story 7 — Garde réseau

## Livré

- `src/waveaudit/securite/garde_reseau.py` (CAP-11, contrats §12, AD-9) :
  - `activer(hotes: list[str])` : résout chaque hôte par `socket.getaddrinfo`, puis, si le garde
    n'est pas déjà actif, sauvegarde et remplace `socket.socket.connect`,
    `socket.socket.connect_ex` et `socket.create_connection`. Idempotente (un second appel
    recalcule la liste d'adresses autorisées mais ne repatch pas et ne duplique pas la
    sauvegarde) ; réinitialise `tentatives()`.
  - Les fonctions remplacées vérifient l'adresse de destination avant de transmettre l'appel à la
    fonction d'origine sauvegardée : une adresse hors liste lève `ConnexionInterdite` et
    l'enregistre dans `tentatives()`, sans jamais atteindre la fonction remplacée (donc sans que
    pytest-socket, ou tout filtre réseau en aval, voie la tentative).
  - `desactiver()` restaure les trois fonctions sauvegardées ; sans effet si le garde est déjà
    inactif.
  - `tentatives() -> list[tuple[str, int]]` : connexions refusées depuis la dernière activation.
  - `@contextmanager garde(hotes)` : active puis désactive, y compris en cas d'exception.
- `tests/unitaires/test_garde_reseau.py` : connexion vers le faux moteur (127.0.0.1) autorisée
  sous garde ; connexion vers `192.0.2.1:80` refusée par `ConnexionInterdite` et enregistrée dans
  `tentatives()` (test sans la fixture `socket_disabled` de pytest-socket, pour que seul un
  `ConnexionInterdite` — pas un `SocketBlockedError` — valide que le garde a levé avant que
  l'appel atteigne la fonction d'origine, donc avant pytest-socket) ; `localhost` résolu vers
  `127.0.0.1` (connexion autorisée par le garde, refusée ensuite par le système faute de
  service, donc une `OSError` qui n'est pas une `ConnexionInterdite`) ; `activer` idempotent ;
  `desactiver` restaure (et sans effet si déjà inactif) ; `ConnexionInterdite` n'est pas une
  `OSError` ; fixture autouse qui désactive le garde et vérifie, après chaque test, que les trois
  fonctions ne sont plus les wrappers du garde (pas de fuite entre tests).

## Écarts au contrat (variantes minimales)

- `socket.socket.connect_ex` lève aussi `ConnexionInterdite` plutôt que de renvoyer un code
  d'erreur (comportement normal de `connect_ex`) : la story et contrats §12 décrivent un
  remplacement unique des trois fonctions avec la même garde, sans distinguer de comportement de
  retour pour `connect_ex` ; lever de façon uniforme est plus sûr et plus simple à tester.
- Au niveau d'exécution, le contrôle compare l'adresse de destination à l'ensemble d'adresses déjà
  résolu par `activer()` (pas de nouvelle résolution par appel), pour éviter toute résolution DNS
  — donc toute sortie réseau potentielle — déclenchée par un appel `connect`/`create_connection`
  vers un nom plutôt qu'une IP littérale.

## Reports

- Intégration dans les commandes `fiches`, `ui` et `banc` (`charger_configuration()` puis
  `with garde(config.reseau.hotes_autorises):`) : hors périmètre de cette story, qui livre
  uniquement le module `garde_reseau` ; `tests/e2e/test_hors_ligne.py` (AD-9) dépend de cette
  intégration et reste à faire avec les stories CLI/UI correspondantes.
