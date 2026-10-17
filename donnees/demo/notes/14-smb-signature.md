---
titre: Partages de fichiers acceptent des sessions sans intégrité vérifiée
actif: 192.0.2.0/24 (serveurs de fichiers internes)
severite_pressentie: moyenne
constat_attendu: INFRA-SMB-SIGNATURE
---
Sur une bonne partie des serveurs du sous-réseau de test (192.0.2.0/24),
l'exigence de signature des échanges de partage de fichiers n'est pas
activée côté serveur (vérifié avec un outil d'énumération réseau, option
désactivée sur 6 des 9 serveurs sondés).

Placé un poste de test en position d'interception sur le même segment et
observé des sessions de partage interceptées et relayées sans que le
serveur cible ne les refuse, en l'absence de signature exigée.

Les 3 serveurs qui exigent la signature ont bien refusé la même
manipulation. Recommandation évidente : aligner tout le parc sur la
configuration des 3 serveurs conformes.
