# Revue — story C4 (Indicateurs de compromission et garde-fous du récit)

Branche revue : `story-C4-revue` (depuis `story-C4` e172280, déjà à jour sur `main` b51f412,
aucun conflit). Décision d'orchestration appliquée : motifs normatifs de `domaine/incident.py`
inchangés, appliqués sur une copie de même longueur où le point final est neutralisé.

## Revue

Constats détaillés : `_bmad-output/specs/spec-waveaudit-cert/stories/story-C4-indicateurs-garde-fous.md`,
section Revue.

- medium — second avis — corrigé : point suivi d'une ponctuation fermante ou séparatrice
  (« (203.0.113.254.) », « 2001:db8::1.) », « (T1059.003.) », « 254... ») non neutralisé.
- low — second avis — rejeté : faux positifs IPv6 de prose (« A::B », « :: ») conformes à §21.
- low — second avis — reporté : fragments résiduels (« (.) », « :443 », « /24 ») hors §21
  étape 4 ; demande une révision du contrat.
- low — reviewer — corrigé : vecteur `REFERENCES_INVENTEES_INCIDENT` importé du faux moteur.
- low — reviewer — corrigé : test d'extraction sur `canoniques.yaml`, attendu écrit à la main.
- Complexité : 0 constat.

## Vérifications

Sonde exécutée sur les cas du second avis avant et après correctif (jeton survivant avant,
retiré après ; versions, horodatages, `T1110.001`, IPv4 mappée connue intacts). Tests ciblés,
suite complète, ruff check et format verts.

## Verdict

Prête à intégrer. Écarts au contrat : aucun nouveau (extension de la neutralisation dans le
cadre de la décision d'orchestration C1). Report : nettoyage des fragments résiduels, à
trancher dans §21.
