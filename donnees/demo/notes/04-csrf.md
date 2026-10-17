---
titre: Changement d'email de compte sans confirmation côté serveur
actif: https://portail.exemple.test/compte/email
severite_pressentie: moyenne
constat_attendu: WEB-CSRF
---
Le formulaire "changer mon adresse email" envoie un POST classique sans
jeton anti-rejeu dans le corps ni dans les en-têtes. Récupéré la requête
dans Burp, reconstruit une page HTML autonome avec un formulaire qui
soumet automatiquement au chargement vers la même URL, avec une adresse
email que je contrôle.

Ouvert cette page piège depuis un onglet où j'étais déjà connecté sur le
portail (session active, cookie présent) : l'adresse du compte a bien été
changée vers la mienne, sans aucune autre interaction de ma part.

Pas de contrôle vu sur l'en-tête d'origine de la requête non plus. Un
attaquant pourrait prendre la main sur un compte juste en faisant visiter
une page piégée à la victime.
