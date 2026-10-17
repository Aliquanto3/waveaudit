---
titre: Page d'erreur très détaillée visible sur l'environnement de production
actif: https://api.exemple.test/commandes/abc
severite_pressentie: moyenne
constat_attendu: CONFIG-DEBUG-ACTIF
---
Envoyé un identifiant de commande volontairement mal formé
(/commandes/abc au lieu d'un nombre) pour voir comment l'API réagit à une
entrée inattendue.

Réponse obtenue : une page d'erreur complète avec la trace d'exécution
détaillée, les noms de fichiers internes du serveur, les numéros de ligne,
et une partie de la configuration de connexion à la base (nom du serveur
et du schéma, sans le mot de passe cette fois).

Ce niveau de détail dans les messages d'erreur, normalement utile
seulement en phase de mise au point, est encore actif sur ce qui semble
être l'environnement réellement utilisé par les clients. Chaque requête
mal formée devient une occasion de récupérer des informations internes.
