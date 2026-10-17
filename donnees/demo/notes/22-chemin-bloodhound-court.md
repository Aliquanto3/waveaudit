---
titre: Export du graphe du domaine, un chemin qui ressort bizarrement court
actif: DOMAINE.LOCAL
severite_pressentie: elevee
constat_attendu: AD-ACL-DANGEREUSE
---
Repris l'export du graphe de l'annuaire (le fichier habituel qu'on
collecte puis qu'on analyse à part) pour chercher des chemins vers le
groupe des admins du domaine. Un compte de service classique
(compte-svc-sauvegarde) a un lien direct en deux sauts :

compte-svc-sauvegarde --(droit complet)--> GPO-Postes-Finance --(appliquée à)--> OU-Finance

Donc un compte qui sert normalement juste à lancer des sauvegardes peut,
via ce droit laissé sur la GPO, modifier ce qui s'applique à toute l'OU
Finance (et donc, in fine, à n'importe quel poste de ce service).

Pas de délégation Kerberos non contrainte détectée sur ce chemin précis
(vérifié à part), et le nombre de comptes dans Admins du domaine est
raisonnable par ailleurs — donc ça ne vient pas de là. Le souci semble
vraiment être ce droit laissé sur l'objet GPO.
