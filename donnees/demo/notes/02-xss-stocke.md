---
titre: Commentaire client persistant non filtré
actif: https://boutique.exemple.test/produit/42
severite_pressentie: elevee
constat_attendu: WEB-XSS-STOCKE
---
Sur la fiche produit, zone "avis clients". Déposé un avis contenant une
balise image bidon avec un gestionnaire onerror. L'avis est accepté sans
modération automatique et s'affiche ensuite pour tout visiteur de la page,
pas seulement pour moi.

Contenu déposé : <img src=x onerror=alert(document.cookie)>

Rechargé la page en navigation privée (donc sans mes cookies de test) : le
code se déclenche quand même à l'ouverture de la fiche produit. Donc
n'importe quel client consultant cette page exécute le script. Stocké en
base, pas juste reflété dans la réponse immédiate.

Autre client potentiellement exposé si l'avis reste public longtemps avant
modération humaine (si elle existe).
