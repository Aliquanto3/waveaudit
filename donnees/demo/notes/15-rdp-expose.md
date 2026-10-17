---
titre: Bureau à distance accessible depuis l'extérieur sur une adresse publique
actif: 192.0.2.50:3389
severite_pressentie: critique
constat_attendu: INFRA-RDP-EXPOSE
---
Scan de l'adresse publique fournie par le client (plage de test
192.0.2.0/24 pour cette note) : le port habituel de bureau à distance
répond directement, sans passer par une passerelle d'accès distant ni par
un VPN.

Capturé la bannière de négociation : aucune authentification réseau
préalable exigée avant l'écran de connexion, et aucun verrouillage de
compte observé après plusieurs tentatives successives avec de faux
identifiants (pas de blocage après 10 essais sur le même compte).

Ce service, directement joignable depuis Internet sans filtrage ni
authentification renforcée, constitue une porte d'entrée exposée à tout
essai automatisé de mots de passe depuis l'extérieur.
