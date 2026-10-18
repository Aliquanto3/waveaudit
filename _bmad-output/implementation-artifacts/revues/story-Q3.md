# Revue — story Q3 (catalogue bilingue et traduction des 50 constats)

Branche `story/Q3`, base 3435669, commit relu d664b1e. Reviewer : Opus, avec la liste du second avis (Haiku).

## Constats

| Sévérité | Source | Constat | Suite |
|---|---|---|---|
| medium | second avis 1 | `_charger` et `verifier` : un `en` présent mais incomplet (champ manquant ou vide) était refusé par `ConstatType.model_validate` avant le contrôle `constat.en is None`, avec le message générique « constat type invalide (...) » au lieu du message §15 « textes anglais manquants (en.<champ>) ». La story documentait ce comportement comme un choix d'interprétation plutôt qu'un défaut. | Corrigé : le bloc `en` brut du YAML est examiné avant `model_validate` (nouvelle fonction `_champs_en_manquants`), dans `_charger` et dans `verifier`. Un `en` absent lève/ajoute toujours le message groupé des 4 champs ; un `en` incomplet lève/ajoute un message par champ réellement manquant ou vide, au format `textes anglais manquants (en.<champ>)`, sans toucher au socle (`domaine/modeles.py`). |
| low | second avis 2 | `test_verifier_detecte_en_incomplet` et `test_charger_leve_configuration_invalide_si_en_incomplet` n'assertaient pas le message §15. | Corrigé : les deux tests vérifient maintenant `textes anglais manquants (en.recommandation)` (`in` pour `verifier`, `match` pour `pytest.raises`). |
| low | second avis 3 | `_verifier_textes_anglais` : boucle morte, pydantic refusait déjà un `en` incomplet avant que `verifier` n'atteigne cette fonction. | Corrigé : fonction supprimée, devenue inutile puisque la complétude de `en` est maintenant garantie par le contrôle brut avant `model_validate`. |
| low | second avis 4 | `_CHAMPS_EN_LISTE` : le message « `en` totalement absent » liste les 4 champs groupés plutôt qu'un message par champ sous la forme `(en.<champ>)`. | Rejeté : ce format groupé est celui documenté littéralement dans la story (« Livré ») pour le cas « absent », et aucun passage de `contrats.md` ou `formats.md` n'impose une ligne par champ dans ce cas précis (seul CAP-8 exige le refus, pas une forme de message) ; cosmétique, sans impact fonctionnel. |
| — | reviewer | Complexité : 0 constat (chargement et vérification en un seul passage par fichier/entrée ; aucune structure qui grossit pendant l'exécution). | — |

## Vérifications

- Échantillon de 10 ids relu (un par famille au moins) : identifiants, références, URL, vecteurs CVSS inchangés ; traduction anglaise correcte et distincte du titre français ; aucun champ `en` vide ni resté en français.
- `motif_langue(en.description, "en") is None` sur les 50 constats (test de qualité dédié) ; aucun faux positif de répétition.
- Contrôle manuel : `verifier()` sur un catalogue de test avec `en` incomplet (1 champ vide) donne désormais `web.yaml:WEB-TEST: textes anglais manquants (en.recommandation)` au lieu de `constat type invalide (...)`, conforme §15. `CatalogueYaml(...).constats()` lève `ConfigurationInvalide` avec le même message.
- `uv run ruff check`, `ruff format --check` : propres. Tests ciblés `tests/unitaires/test_catalogue.py` : 27 passés. Suite complète : 862 passés, 2 désélectionnés (`slow`).
