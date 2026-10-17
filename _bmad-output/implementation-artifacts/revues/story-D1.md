# Revue story D1 : catalogue élargi et notes difficiles

Branche `story-D1-revue` (depuis `story-D1`, rebasée sur main). Contrat : stories.yaml D1, contrats §15 et §16, contraintes story 11.

Vérifié : 50 constats (ajouts seulement, 35 figés intacts), notes 01-20 inchangées, aucune note 21-30 ne contient l'identifiant ou le titre de son constat, données fictives (192.0.2.0/24, exemple.test). Rattachement : 01-20 top1 17/20, top3 20/20 ; 21-30 top1 8/10, top3 10/10.

| Sévérité | Source | Constat | Décision |
|---|---|---|---|
| medium | reviewer | test_cli (story 13) attendait 20 notes après rebase | corrigé (30) |
| low | second avis 1 | constat_attendu contre liste figée | corrigé (vrai catalogue) |
| low | second avis 2 | xfail impératif | rejeté (marqueur statique, effet identique) |
| low | second avis 3 | clé AES d'aspect réel, note 27 | corrigé (clé manifestement fictive) |
| low | second avis 4 | 6 constats sans note | rejeté (non exigé) |
| low | second avis 5 | AV:A sur ACL et ESC1 | rejeté (convention AD du catalogue) |

Complexité : 0 constat. Reports : aucun.
