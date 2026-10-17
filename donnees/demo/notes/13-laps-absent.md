---
titre: Même compte local identique sur tout le parc de postes
actif: parc bureautique, environ 180 postes
severite_pressentie: elevee
constat_attendu: AD-LAPS-ABSENT
---
Testé le compte administrateur local récupéré sur un premier poste
(hachage extrait après compromission de ce poste lors d'un autre test) sur
une dizaine d'autres postes du même parc, pris au hasard dans l'annuaire.

Résultat : accès administrateur local obtenu sur l'ensemble des postes
testés, sans jamais avoir besoin du mot de passe en clair (réutilisation
directe du hachage). Aucune solution de rotation automatique du mot de
passe administrateur local n'a été trouvée configurée côté annuaire.

Conséquence pratique : la compromission d'un seul poste suffit à ouvrir
l'administration locale de tout le parc, ce qui facilite énormément le
déplacement latéral d'un poste à l'autre.
