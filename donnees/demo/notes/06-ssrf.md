---
titre: L'aperçu d'image par URL contacte des adresses internes
actif: https://api.exemple.test/apercu?url=
severite_pressentie: elevee
constat_attendu: WEB-SSRF
---
Fonction "aperçu" qui prend une URL en paramètre et renvoie une miniature
de l'image pointée. Essayé de la faire taper sur une adresse qui n'est
clairement pas publique :

GET /apercu?url=http://192.0.2.10/admin

Le serveur a mis plusieurs secondes avant de répondre une erreur de
format, ce qui montre qu'il a bien tenté la connexion lui-même (le délai
correspond à une tentative de connexion qui échoue, pas à un refus
immédiat).

Essayé ensuite une URL vers un service de métadonnées cloud factice sur le
même sous-réseau de test (192.0.2.1) : comportement similaire. Le serveur
applicatif semble capable de requêter n'importe quelle adresse depuis le
réseau interne à la demande d'un utilisateur externe.
