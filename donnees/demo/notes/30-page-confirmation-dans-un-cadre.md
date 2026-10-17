---
titre: La page de confirmation de virement s'affiche... dans un cadre
actif: https://banque-pro.exemple.test/virement/confirmer
severite_pressentie: moyenne
constat_attendu: WEB-CLICKJACKING
---
Construit une page de test toute simple (un cadre HTML pointant vers la
page de confirmation de virement, rendu quasi transparent par-dessus un
faux bouton "Voir mon solde") et ouverte dans un navigateur avec une
session active sur banque-pro.exemple.test.

La page de confirmation s'affiche normalement dans le cadre, sans aucun
message d'erreur ni refus du navigateur. Aucun en-tête limitant
l'affichage dans un cadre tiers n'a été vu dans les réponses de cette
page pendant le test (vérifié via les outils de développement du
navigateur).

Le bouton de confirmation réel, invisible, était positionné exactement
sous le faux bouton "Voir mon solde" affiché par-dessus.
