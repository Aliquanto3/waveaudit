---
titre: Retour d'un outil de diagnostic TLS sur le portail extranet
actif: https://extranet.exemple.test
severite_pressentie: moyenne
constat_attendu: CRYPTO-CERTIFICAT-INVALIDE
---
Extrait brut d'un scanner TLS en ligne de commande (sortie un peu dense,
gardée telle quelle) :

```
 TLS 1.2      offered
 TLS 1.3      offered
 Cipher Groups (client)
   ECDHE       offered
 Certificate Chain
   #1 CN=extranet.exemple.test (subject) <-- #2 CN=extranet.exemple.test (issuer)
   Chain of trust               NOT ok (self signed CA in chain)
```

Côté protocoles et suites, tout est à jour (TLS 1.2/1.3, suites modernes
uniquement), donc ce n'est pas un souci de version obsolète. Le point qui
coince est plus bas dans le rapport : la chaîne de certification ne
remonte à aucune autorité reconnue, le certificat du serveur étant signé
par une autorité créée en interne et jamais distribuée aux postes
clients.

Confirmé en se connectant depuis un navigateur grand public sans
exception ajoutée au préalable : avertissement de sécurité bloquant
avant d'accéder au portail.
