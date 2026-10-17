---
titre: Authentification contournée sur l'espace pro
actif: https://espace-pro.exemple.test/login
severite_pressentie: critique
constat_attendu: WEB-INJECTION-SQL
---
Formulaire de connexion de l'espace pro. Champ identifiant testé avec une
valeur classique de contournement :

identifiant = admin' OR '1'='1
mot_de_passe = n'importe quoi

Résultat : connecté directement en tant qu'admin, sans connaître le vrai
mot de passe. La requête côté base semble concatener la valeur saisie sans
paramétrage.

Essayé aussi une temporisation (SLEEP) sur le même champ : la réponse met
nettement plus de temps à revenir, ce qui confirme que la valeur atteint
bien le moteur de base de données tel quel.

Impact direct : accès complet à l'espace pro sans identifiants valides,
donc probablement à toutes les données clients qu'il expose.
