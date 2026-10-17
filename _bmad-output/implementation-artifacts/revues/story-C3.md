# Revue story C3 — Catalogue de règles et moteur de détection

Branche `story-C3-revue` (depuis `story-C3`, rebasée sur `main` sans conflit).

## Constats

- medium — second avis — corrigé : fenêtre glissante en O(n²) par groupe (comptes
  recalculés à chaque candidat `k` et à chaque extension de `f`), environ 10 min estimées
  à 100 000 événements d'un même groupe. Réécrite dans `_fenetres` (un pointeur `lo`
  monotone, O(n)) avec les mêmes comparaisons `t_k - t_j <= fenetre_s` que le pseudo-code,
  donc les mêmes résultats, flottants compris. Oracle : transcription littérale du
  pseudo-code de contrats §21 dans le test, comparée sur 3 000 jeux aléatoires à graine fixe
  (doublons d'horodatage, fractions de seconde, seuil 1, fenêtre 0, bornes égales) et sur
  des cas limites paramétrés. Test de performance : 50 000 événements, un seul groupe,
  moins de 5 s (environ 1,3 s mesurées, construction comprise).
- low — second avis — rejeté (point à arbitrer, comportement inchangé) : pas de
  dédoublonnage dans `detecter`. Le §21 n'en prévoit pas ; l'unicité de `Evenement.cle`
  vient de la lecture (C2 : un événement par ligne lue, un nom par fichier du dossier).
  Seule l'union du rapport (§21 « Indicateurs ») dédoublonne par `cle`, pour les événements
  partagés entre détections. Si un appelant pouvait repasser deux fois la même liste, à
  trancher au niveau de C5, pas de C3.
- Complexité : 1 constat (le medium ci-dessus). `correspond` est appelée une fois par
  couple (règle, événement), en O(R × n) ; le tri final est en O(n log n) : sans objet.

## Vérifications

15 règles couvertes en positif par `canoniques.yaml`, 15 entrées négatives (bénignes et
voisines) ; vecteurs normatifs de §21 en tests. 503 tests verts (suite complète), ruff
check et format verts.

## Verdict

Prête à intégrer. Aucun écart au contrat.
