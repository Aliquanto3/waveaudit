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
- Au niveau d'exécution, le contrôle compare la destination à l'ensemble déjà résolu par
  `activer()` (IP résolues et noms de la liste, sans nouvelle résolution par appel), pour éviter
  toute résolution DNS — donc toute sortie réseau potentielle — déclenchée par un appel vers un
  nom hors liste.
- Revue : `sendto`/`sendmsg` aussi remplacés ; `garde` imbriqué n'éteint pas l'englobant.

## Reports

- Intégration dans les commandes `fiches`, `ui` et `banc` (`charger_configuration()` puis
  `with garde(config.reseau.hotes_autorises):`) : hors périmètre de cette story, qui livre
  uniquement le module `garde_reseau` ; `tests/e2e/test_hors_ligne.py` (AD-9) dépend de cette
  intégration et reste à faire avec les stories CLI/UI correspondantes.
- Limite connue, à vérifier avec la story UI ou moteur : sous Windows, une connexion asyncio
  (`ProactorEventLoop`, `ConnectEx`) ne passe pas par `socket.socket.connect` et échappe au garde
  (pytest-socket a la même limite). Le moteur actuel est synchrone (httpx/httpcore →
  `socket.create_connection`) ; si un client asynchrone sortant apparaît, ajouter un test e2e
  sous garde qui exige `ConnexionInterdite` vers 192.0.2.1 depuis ce client.

## Revue

- high, second avis 1 — garde imbriqué (test e2e autour d'une commande qui pose son propre garde) : la sortie du garde interne désactivait l'englobant et `activer` vidait `tentatives()`. Corrigé : `garde` imbriqué ajoute ses hôtes puis rend la liste précédente, sans désactiver ni vider ; test ajouté.
- medium, second avis 5 — `localhost` est dans `hotes_autorises` par défaut, mais `create_connection(("localhost", p))` (httpx vers `http://localhost:…`) levait `ConnexionInterdite`. Corrigé : les noms de la liste sont autorisés tels quels (la connexion IP qui suit est revérifiée) ; un nom hors liste reste refusé sans résolution DNS (test).
- medium, second avis 2 — UDP non connecté (`sendto`, `sendmsg`) contournait le garde, contraire à l'esprit d'AD-9 (télémétrie UDP). Corrigé : `sendto` et `sendmsg` (s'il existe) remplacés ; test `sendto` aux deux signatures. Variante au-delà de la liste de contrats §12.
- medium, second avis 3 — la fixture anti-fuite désactivait avant de vérifier (fuite masquée ; `test_activer_idempotent` laissait le garde actif). Corrigé : vérification avant nettoyage (`_actif` faux, aucune fonction remplacée) ; comparaison à l'identité d'avant le test impossible car pytest-socket retire son `connect` avant la fixture.
- low, second avis 4 — fonction capturée sous garde puis appelée après : `KeyError`. Corrigé : `_originaux` conservé, les remplacements transmettent quand le garde est inactif ; test. Lectures hors verrou dans `_verifier` : rejeté (lecture d'une référence de frozenset et `list.append` atomiques sous le GIL).
- low, second avis 6 — résolution des noms dans `activer` hors garde : rejeté, conforme à contrats §12 (noms locaux de la configuration).
- low, second avis 7 — tests manquants (connect_ex, imbrication, sendto, nom) : corrigé ; threads non testés (rejeté, état global sous verrou).
- low, revue — asyncio Proactor sous Windows échappe au garde : reporté (voir Reports).
- Complexité : 0 constat (`tentatives()` copie la liste à la demande seulement ; `_verifier` en O(1)).
