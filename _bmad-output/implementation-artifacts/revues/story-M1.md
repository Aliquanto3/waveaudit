# Revue — story M1 (verrou unique et moteur à la demande)

Branche `story/M1`, commit relu a384135 (base main db81ae3). Relecteur : Opus, avec la liste du
second avis (Haiku). Verdict : conforme à contrats §24 et [revue A10/E1/E10] après correctifs.

## Constats

| Sévérité | Source | Constat | Suite |
|---|---|---|---|
| medium | second avis 1 | `test_minuterie_concurrente_sans_fermeture_pendant_usage` vacueux : aucune minuterie n'échoit pendant la boucle. Mesuré : même le mutant qui retire **les deux** gardes de `_echeance` passe (3/3). Le mutant cité (garde `_usages` seule retirée) est en revanche équivalent : la garde d'identité suffit, chacune couvre l'autre. | Corrigé : pauses autour de la minuterie, pause commune toutes les 10 itérations (barrière) et assertion d'au moins une échéance réelle (`len(serveurs) > 1`, 20/20 verts) ; nouveau test déterministe `test_echeance_perimee_ne_ferme_pas` (rappel déjà parti pendant un usage, puis minuterie périmée après réarmement) qui tue les trois mutants. |
| low | second avis 2 | `except Exception: pass` dans `_echeance` : un échec d'arrêt du llama-server disparaît sans trace. | Corrigé : `_log.warning(..., exc_info=True)`. L'état reste remis à zéro avant l'arrêt (choix du dev, évite de réutiliser un moteur à moitié fermé). |
| low | second avis 3 | `liberer` et `definir` ne vérifient pas le propriétaire. | Rejeté : signature figée par §24 (pas de jeton) ; un seul fil de travail tient le verrou et le rend dans son `finally` (W2). |
| low | second avis 4 | `utiliser("B")` pendant un usage de "A" ferme A. | Reporté W2 (déjà dans les reports de la story) : §24 impose l'appel sous `VerrouUnique`. |
| low | relecteur | `_ouvrir_moteur` (démarrage et sonde, jusqu'à `delai_demarrage_s`) s'exécute sous le verrou interne : `fermer()` attend la fin d'une ouverture en cours. | Reporté W2 : à vérifier avec l'attente de 10 s du lifespan (E3) ; sans effet hors arrêt de l'application. |
| — | écart déclaré | `composition.ouvrir` reçoit le nom résolu au lieu de `modele`. | Accepté : équivalent en externe (`modele or modele_api`) et en local-gere (`par_nom` du même artefact) ; c'est ce qui fige le choix défaut/repli de E10 (sinon la RAM du moment pourrait ouvrir un autre modèle que la clé). |

Complexité : 0 constat (aucune structure qui grossit).

## Vérifications

- Tests ciblés `test_moteur_demande.py` et `test_composition.py` verts ; test concurrent 20/20.
- Mutants de `_echeance` (`if False`, garde `_usages` seule, garde d'identité seule) tués par le
  test déterministe ; le test concurrent seul ne les tue pas (fenêtre de course trop étroite),
  il prouve l'absence de fermeture pendant un usage sur des échéances réelles.
- Suite complète : 755 passed, 2 deselected ; `ruff check` et `ruff format --check` propres.
- Aucun fichier du socle AD-0, ni `composition.py`, modifié.
