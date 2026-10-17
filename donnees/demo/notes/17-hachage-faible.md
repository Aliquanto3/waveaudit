---
titre: Les mots de passe clients semblent stockés avec un algorithme ancien
actif: export de la base clients (échantillon anonymisé fourni par le client)
severite_pressentie: elevee
constat_attendu: CRYPTO-HACHAGE-FAIBLE
---
Sur l'échantillon de base fourni pour le test (quelques centaines de
lignes anonymisées sur les autres colonnes), la colonne "mot de passe"
contient des valeurs de longueur fixe caractéristiques d'un algorithme de
hachage générique et rapide, sans sel visible associé par ligne.

Pris une dizaine de ces valeurs et lancé un essai de cassage hors ligne sur
une machine de test banale avec une liste de mots courante : plusieurs
sont retrouvées en quelques minutes, ce qui confirme l'absence de
ralentissement volontaire de l'algorithme.

Un tel algorithme, pensé pour aller vite, n'est pas adapté au stockage de
secrets : une fuite de cette table rendrait la majorité des mots de passe
récupérables très rapidement, à coût matériel très faible.
