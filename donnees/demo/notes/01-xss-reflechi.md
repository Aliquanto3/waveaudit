---
titre: Champ de recherche vulnérable sur le portail client
actif: https://portail.exemple.test/recherche?q=
severite_pressentie: elevee
constat_attendu: WEB-XSS-REFLECHI
---
Testé le champ de recherche en haut de page. Le paramètre q est renvoyé tel
quel dans le bloc de résultats, sans aucun échappement.

Requête envoyée :
GET /recherche?q=<script>document.title='pwn'</script> HTTP/1.1
Host: portail.exemple.test

Le script s'exécute dans le navigateur, confirmé via Burp + un navigateur
jetable. Un lien piégé envoyé à un utilisateur connecté suffirait à
détourner sa session. Rien côté serveur ne filtre les chevrons.

À creuser : vérifier si d'autres champs de formulaire (filtre catégorie,
tri) ont le même souci.
