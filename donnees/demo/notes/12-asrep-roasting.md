---
titre: Comptes sans vérification d'identité préalable au premier échange
actif: DOMAINE.LOCAL
severite_pressentie: moyenne
constat_attendu: AD-ASREP-ROASTING
---
En énumérant les comptes du domaine, repéré trois comptes dont l'option
"ne pas exiger de vérification préalable" est activée (visible dans les
attributs du compte, sans besoin d'y être authentifié).

Pour ces trois comptes, un simple échange initial auprès du contrôleur de
domaine, sans connaître leur secret, suffit à récupérer un élément chiffré
réutilisable pour une tentative de cassage hors ligne. Un des trois est
tombé assez vite avec une liste de mots de passe classiques (prénom +
année).

Ce compte n'a pas de droits particuliers constatés pour l'instant, mais
c'est un point d'entrée facile et difficile à détecter côté journalisation
puisqu'aucune tentative d'authentification ratée n'est générée.
