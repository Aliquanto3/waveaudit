---
titre: L'API clients répond avec un partage d'origine trop large
actif: https://api.exemple.test/moi
severite_pressentie: moyenne
constat_attendu: WEB-CORS-PERMISSIF
---
Requête vers /moi (renvoie les infos du compte connecté, en JSON) depuis
un site de test que je contrôle, hébergé sur attaquant.local, en ajoutant
un en-tête Origin bidon pointant vers ce domaine.

Réponse observée :
Access-Control-Allow-Origin: https://attaquant.local
Access-Control-Allow-Credentials: true

Le serveur reflète apparemment n'importe quelle origine demandée dans
l'en-tête de requête, et autorise en plus l'envoi des cookies de session
avec la réponse. Depuis une page hébergée sur mon domaine de test, j'ai pu
lire en JavaScript les données du compte connecté de la victime, cookies
inclus dans la requête.

Aucune liste blanche de domaines visible côté serveur.
