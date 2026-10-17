---
titre: Dépôt de photo de profil accepte un script serveur
actif: https://portail.exemple.test/profil/photo
severite_pressentie: elevee
constat_attendu: WEB-UPLOAD-NON-RESTREINT
---
Formulaire de dépôt de photo de profil. Déposé un fichier renommé en
avatar.php contenant un code d'exécution de commande très basique, en
intervertissant juste le type MIME annoncé pour qu'il ressemble à une
image.

Le dépôt est accepté sans message d'erreur, et le fichier se retrouve
accessible directement à une URL prévisible du type
/uploads/avatar_12.php. En l'ouvrant dans le navigateur, la commande
passée en paramètre s'exécute côté serveur (testé avec un simple affichage
de la liste des dossiers, rien de destructeur).

Aucun contrôle de contenu réel (juste le nom déclaré), et le dossier de
dépôt sert visiblement des fichiers exécutables par le serveur web.
