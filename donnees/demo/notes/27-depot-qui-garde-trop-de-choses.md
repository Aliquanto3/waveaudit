---
titre: Un depot interne qui garde un peu trop de choses en memoire
actif: https://git-interne.exemple.test/outils/facturation
severite_pressentie: elevee
constat_attendu: CRYPTO-SECRET-DANS-LE-CODE
---
En parcourant l'historique de versionnage du dépôt "outils/facturation"
(accès en lecture obtenu via un compte de test), un ancien commit vieux
de deux ans contient encore :

```
AES_KEY = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"
```

Le commit suivant "retire" la clé du fichier actuel, mais elle reste
parfaitement lisible dans l'historique pour qui clone le dépôt en
entier. Cette même clé semble être celle utilisée pour chiffrer les
exports de facturation (nom de variable repris à l'identique dans le
code de génération des exports), donc ce n'est pas juste un mot de passe
de test oublié : c'est bien une clé de chiffrement figée, partagée par
tous les environnements qui réutilisent ce dépôt.
