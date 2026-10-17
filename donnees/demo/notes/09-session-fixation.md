---
titre: L'identifiant de session ne change pas après connexion
actif: https://portail.exemple.test/login
severite_pressentie: moyenne
constat_attendu: WEB-SESSION-FIXATION
---
Avant toute connexion, le site pose déjà un cookie de session (visible dans
l'onglet stockage du navigateur). Noté sa valeur, puis utilisé un lien de
connexion forgé qui fixe explicitement ce même cookie côté navigateur
avant la saisie du mot de passe (technique classique de fixation).

Après connexion réussie avec des identifiants valides, le cookie de
session garde strictement la même valeur qu'avant l'authentification. Si
j'avais pu faire connaître cette valeur à une victime avant qu'elle se
connecte (lien piégé, sous-domaine partagé...), j'aurais récupéré une
session authentifiée en sa place.

Pas de renouvellement observé à l'étape de connexion, ni à l'étape de
déconnexion-reconnexion successive.
