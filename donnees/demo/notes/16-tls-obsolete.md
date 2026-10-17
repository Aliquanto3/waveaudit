---
titre: Le portail accepte encore d'anciennes versions de chiffrement de transport
actif: https://portail.exemple.test
severite_pressentie: moyenne
constat_attendu: CRYPTO-TLS-OBSOLETE
---
Testé la négociation du chiffrement de transport sur le portail avec un
outil dédié. Le serveur accepte toujours une version ancienne du protocole
(datant d'il y a plus de dix ans), ainsi qu'un jeu de suites considérées
comme faibles (chiffrement par bloc en mode obsolète, sans authentification
d'intégrité moderne).

Forcé un navigateur de test à négocier volontairement l'ancienne version :
la connexion s'établit sans avertissement particulier côté serveur. Un
attaquant en position d'interception réseau pourrait forcer ce repli vers
la version la plus faible acceptée.

Les versions récentes du protocole sont bien proposées en priorité, mais
rien n'empêche le repli vers les anciennes.
