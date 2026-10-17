---
titre: Connexion au vpn, rien d'autre demande apres le mot de passe
actif: https://vpn.exemple.test
severite_pressentie: moyenne
constat_attendu: AUTRE-MFA-ABSENTE
---
Test de connexion au VPN avec un compte de test fourni par le client.
Après le mot de passe, la session s'ouvre directement : aucune demande
de code supplémentaire, d'application mobile, ni de clé physique.

Demandé confirmation à l'équipe IT : pour l'instant, ce même parcours
vaut pour tous les comptes, y compris ceux des administrateurs qui se
connectent à distance pour gérer l'infrastructure. Un unique facteur (le
mot de passe) protège donc l'accès au réseau interne depuis l'extérieur,
quel que soit le niveau de privilège du compte qui se connecte.
