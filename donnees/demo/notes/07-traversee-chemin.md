---
titre: Téléchargement de fichiers internes via le visualiseur de documents
actif: https://docs.exemple.test/voir?fichier=
severite_pressentie: critique
constat_attendu: WEB-TRAVERSEE-CHEMIN
---
Fonction qui affiche un document dont le nom est passé en paramètre
(rapports.pdf, facture.pdf...). Essayé de remonter l'arborescence :

GET /voir?fichier=../../../../etc/passwd

Réponse : contenu d'un fichier système classique, en clair dans la
réponse HTTP. Même chose en remplaçant le séparateur par des variantes
encodées (%2e%2e%2f) au cas où un filtre basique bloquerait la forme
simple : ça passe aussi.

Donc le paramètre est concatené directement à un chemin de base sans
normalisation ni vérification que le résultat reste dans le dossier prévu.
Potentiellement tout fichier lisible par le compte de service applicatif
est récupérable de cette façon.
