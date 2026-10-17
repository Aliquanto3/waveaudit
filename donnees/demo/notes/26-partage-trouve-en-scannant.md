---
titre: Partage de fichiers trouvé en scannant le réseau serveurs
actif: 192.0.2.55
severite_pressentie: elevee
constat_attendu: INFRA-NFS-EXPORTE
---
Sortie d'une commande de listage d'exports sur un serveur de fichiers du
réseau serveurs :

```
Export list for 192.0.2.55:
/data/partage-commun *
/data/sauvegardes     192.0.2.0/24
```

Le premier export (partage-commun) est exporté vers tout le monde (le
fameux astérisque), sans restriction d'hôte. Monté depuis un poste qui
n'a rien à voir avec ce serveur, sans aucune authentification côté
partage, et le contenu (documents RH visiblement) était lisible
directement.

Pas regardé en détail les options d'export exactes faute de temps, mais
l'absence de toute restriction d'hôte suffit déjà à inquiéter.
