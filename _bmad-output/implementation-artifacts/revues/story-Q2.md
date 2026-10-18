# Revue — story Q2 (garde-fous v2)

Branche `story/Q2`, base db81ae3, commit relu b23244e. Reviewer : Opus, avec la liste du second avis (Haiku).

## Constats

| Sévérité | Source | Constat | Suite |
|---|---|---|---|
| medium | second avis 1 | `_ecriture_non_latine` comparait des jetons séparés par des espaces à la source : « Жертва, » cité depuis « Жертва » donnait `écriture non latine`. Le contrat §6 v2 (revue E35/E36) parle de lettre présente dans la source. | Corrigé : comparaison par lettre (casse comprise ou repliée). Test `test_non_latin_cite_avec_ponctuation_collee`. |
| low | second avis 2 | `(.{3,50}?)\1{4,}` + `len(m.group(0)) >= 40` : 40 ou 41 `A` donnent une suite de 39, non retenue. | Rejeté : conforme au motif du contrat ; une boucle de moins de 40 caractères est sans impact (les rubriques dégénérées mesurées font jusqu'à 1 200 caractères). |
| low | second avis 3 | Les trigrammes ignorent la source : une énumération répétitive légitime est signalée. | Rejeté : conforme au contrat (la source ne s'applique qu'à la boucle) ; effet = `a_revoir`, texte conservé, le consultant tranche. |
| low | reviewer | `_boucle_sans_espace` parcourt toutes les correspondances (`finditer`) là où le contrat écrit `re.search`. | Accepté : avec `re.search`, une première suite sans lettre (`=====`) masquerait une vraie boucle plus loin ; `finditer` suit l'intention du contrat. |
| low | reviewer | Comparaison à la source en `casefold` (boucle), là où le contrat dit « telle quelle ». | Écart à arbitrer, déclaré dans la spec de story ; sans effet mesuré. |
| low | reviewer | Source incident élargie aux ids/IP/hachages légitimes (contrat : lignes de preuve seulement). | Écart à arbitrer, déclaré dans la spec de story ; ne peut que réduire les faux positifs. |

Complexité : 0 constat (aucune structure qui grossit ; un passage linéaire par rubrique).

## Vérifications

- Ordre des étapes, seuils (5/20), URL de la note (jeton entier, préfixe retiré), mots-outils (listes, citations, sigles, `3DES`), titre hors mots-outils, branchement fiches et incident : conformes.
- Données réelles (`var/sorties/`, 19 lots, 264 rubriques, source vide) : 3 rubriques signalées, celles de la mesure du contrat (deux répétitions, la note 26 en japonais), aucun autre faux positif.
- `uv run ruff check`, `ruff format --check` : propres. Suite complète : 779 passés, 2 désélectionnés (`slow`).
