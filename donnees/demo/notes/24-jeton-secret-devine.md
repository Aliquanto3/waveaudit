---
titre: Le jeton du portail partenaire resemble a un secret de demo
actif: https://partenaires.exemple.test/api
severite_pressentie: elevee
constat_attendu: WEB-JWT-FAIBLE
---
En décodant le jeton renvoyé après connexion (partie visible, juste pour
lire l'en-tête et les claims), rien d'anormal dans le contenu. Par contre
en testant la vérification de signature avec quelques mots courants
("partenaire2024", "changeit", le nom du produit en minuscule...), un
essai a fini par matcher.

Une fois le secret retrouvé, possible de refabriquer un jeton avec
role=admin a la place de role=lecture, et l'API l'a accepté sans
broncher.

A noter : l'algorithme annoncé dans l'en-tete du jeton est HS256, donc le
secret est bien partagé cote serveur, pas une histoire de cle publique et
privee séparées.
