---
titre: Mot de passe de connexion à la base trouvé dans un fichier de configuration public
actif: https://portail.exemple.test/static/config.bak
severite_pressentie: critique
constat_attendu: CONFIG-SECRETS-EN-CLAIR
---
En explorant les dossiers accessibles directement sous /static, tombé sur
un fichier de sauvegarde de configuration qui n'aurait pas dû être exposé
(config.bak). Le fichier s'ouvre normalement dans un navigateur, sans
aucune authentification.

Contenu en clair : une ligne de connexion à la base de données avec
identifiant et mot de passe en texte brut, ainsi qu'une clé utilisée pour
signer les jetons de session de l'application.

Pas eu le temps (ni l'autorisation) de valider ces identifiants sur la
vraie base pendant le test, mais leur simple présence en clair dans un
fichier joignable depuis Internet est déjà en soi une exposition majeure
qui pourrait donner un accès direct aux données si récupérée par un tiers.
