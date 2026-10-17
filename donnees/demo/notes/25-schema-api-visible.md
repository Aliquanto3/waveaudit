---
titre: Un coup d'oeil sur l'API du nouvel espace client
actif: https://espace-client.exemple.test/graphql
severite_pressentie: faible
constat_attendu: WEB-GRAPHQL-INTROSPECTION
---
Requête envoyée telle quelle depuis un client HTTP générique, sans
aucune authentification :

```
POST /graphql
{"query":"{__schema{types{name fields{name}}}}"}
```

Réponse : la totalité du schéma, avec entre autres un type
"CompteInterne" et une mutation "reinitialiserMotDePasseAdmin" qui ne
sont visibles nulle part dans la documentation publique de l'espace
client.

Pas eu le temps de vérifier si ces champs sont eux-mêmes protégés
correctement derrière une autorisation côté serveur — juste leur
existence qui est déjà une information qui ne devrait pas sortir comme
ça sans y être invité.
