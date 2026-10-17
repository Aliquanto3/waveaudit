---
titre: Note avec une sévérité pressentie non reconnue
actif: https://exemple.test
severite_pressentie: catastrophique
---
Le champ severite_pressentie ci-dessus ne fait pas partie de la liste
autorisée (critique, elevee, moyenne, faible, info). La note reste
valide : ce champ doit simplement être ignoré (ramené à None), sans faire
échouer la lecture du reste de la note.
