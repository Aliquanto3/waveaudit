---
titre: Aucune trace des tentatives de connexion échouées sur l'espace pro
actif: https://espace-pro.exemple.test/login
severite_pressentie: faible
constat_attendu: AUTRE-JOURNALISATION-INSUFFISANTE
---
Pendant les autres tests sur le formulaire de connexion de l'espace pro,
une centaine de tentatives avec des identifiants invalides ont été
envoyées sur une courte période, pour vérifier le comportement du
formulaire.

Demandé ensuite au client de vérifier côté journaux applicatifs et côté
équipement de sécurité périmétrique si quelque chose avait été enregistré
ou remonté : rien n'apparaît, ni dans les journaux de l'application, ni
dans une quelconque alerte de supervision.

Sans trace d'un tel volume de tentatives sur un délai aussi court, une
tentative réelle d'essai massif de mots de passe sur ce formulaire
passerait totalement inaperçue, ce qui retarderait beaucoup toute
détection ou réaction en cas d'incident.
