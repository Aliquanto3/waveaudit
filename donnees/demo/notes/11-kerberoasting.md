---
titre: Comptes de service avec un secret facile à retrouver hors ligne
actif: DOMAINE.LOCAL
severite_pressentie: elevee
constat_attendu: AD-KERBEROASTING
---
Demandé les tickets de service pour tous les comptes porteurs d'un
attribut de service applicatif, depuis un compte utilisateur standard
sans aucun privilège particulier. Récupéré une dizaine de tickets chiffrés
sans difficulté, aucune alerte visible côté supervision pendant le test.

Passé ces tickets au cassage hors ligne sur une liste de mots courante :
deux comptes de service (dont un lié à un ordonnanceur de tâches) sont
tombés en quelques minutes, secret du type "Service2023!".

Un de ces comptes de service appartient au groupe des opérateurs de
sauvegarde, ce qui donne un accès large une fois le secret connu. Aucune
authentification multi-facteurs possible sur ce type de compte.
