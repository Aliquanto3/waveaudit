---
titre: Accès aux factures d'un autre client en changeant un numéro
actif: https://portail.exemple.test/factures/1042
severite_pressentie: elevee
constat_attendu: WEB-IDOR
---
Connecté avec mon compte de test, j'ai ouvert ma propre facture :
/factures/1042. En changeant juste le nombre en fin d'URL (1041, 1040,
1039...) j'arrive sur les factures d'autres comptes, avec nom, adresse
postale et montants visibles, toujours avec ma session à moi.

Aucun message d'erreur, aucune redirection : la page renvoie directement
le contenu demandé. Pas de vérification que la facture appartient au
compte connecté.

Testé une dizaine de numéros consécutifs, tous accessibles de la même
façon. Potentiellement toutes les factures de la plateforme sont dans ce
cas si les numéros sont séquentiels.
