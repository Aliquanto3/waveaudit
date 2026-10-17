---
titre: Retour de scan sur le pare-feu, un port bizarre niveau management
actif: 192.0.2.40
severite_pressentie: elevee
constat_attendu: INFRA-IPMI-EXPOSE
---
Sortie nmap collée telle quelle (le coeur du rapport), scan lancé sur la
plage de management du client :

```
Nmap scan report for 192.0.2.40
PORT     STATE SERVICE
623/udp  open  asf-rmcp
443/tcp  open  https
```

Le port 623 correspond en général à une interface de gestion carte mère
(souvent appelée BMC ou équivalent). Testé une connexion avec l'outil en
ligne de commande habituel, en forçant le chiffrement "0" (celui qu'on
essaie toujours en premier par acquis de conscience) : la carte a répondu
normalement, comme si l'authentification n'était pas vérifiée du tout.

Pas eu le temps de creuser plus avant la fin du créneau, mais ça sent
l'accès admin sans friction sur l'hyperviseur derrière.

Autre point relevé en passant : le serveur esr joignable depuis le réseau
bureautique, pas seulement depuis le réseau d'administration.
