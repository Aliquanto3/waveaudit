---
titre: Message d'erreur etrange sur le generateur de devis en ligne
actif: https://devis.exemple.test/generer
severite_pressentie: elevee
constat_attendu: WEB-SSTI
---
Le formulaire de génération de devis permet de personnaliser un champ
"objet" qui apparaît ensuite dans le PDF généré. En testant avec une
valeur contenant des accolades doubles (un réflexe après avoir lu un
article sur le sujet), le serveur a renvoyé une erreur 500 avec, dans le
corps de la réponse, une trace mentionnant un moteur de rendu de
gabarits connu et une erreur de type "attribut manquant sur un entier".

En renvoyant une expression arithmétique entre doubles accolades à la
place d'un texte normal dans ce même champ, le résultat du calcul
apparaît tel quel dans le PDF généré, à l'endroit où le texte était
attendu. Donc le contenu du champ n'est pas juste affiché : il est
évalué avant d'être inséré dans le document.
