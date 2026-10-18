# Formats v2 : catalogue bilingue, état de relecture, exports

Ce fichier complète `../spec-waveaudit-poc/formats.md`. Il décrit les données en termes de contenu ; l'architecture en fixe le schéma normatif dans `contrats.md`.

## Langue d'un lot (CAP-8)

Le lot a une valeur `fr` (par défaut) ou `en`, fixée au lancement et non modifiable ensuite. Elle détermine la consigne envoyée au moteur, les textes du constat type passés dans le prompt, la langue que vérifie le garde-fou (CAP-4) et les libellés du Word.

## Constat type bilingue (CAP-8)

| Champ | Par langue | Remarque |
|---|---|---|
| `id`, `famille`, `cvss_vecteur`, `source` | non | inchangés |
| `titre`, `description`, `impact`, `recommandation` | oui (`fr`, `en`) | les deux langues sont obligatoires |
| `mots_cles` | non | ils couvrent déjà le français et l'anglais |
| `references` (`id`, `titre`, `url`) | non | les titres des références ne sont pas traduits |

`catalogue verifier` refuse une entrée à laquelle il manque l'une des deux langues. La traduction anglaise (identifiants, références et URL inchangés ; titre et textes traduits) est rédigée par le développeur de la story qui introduit ou modifie l'entrée ; Anaël relit un échantillon de 10 constats avant fusion. L'index BM25 est bilingue : chaque constat y entre dans ses deux langues, quelle que soit la langue du lot en cours de rattachement.

## État de relecture d'un lot (CAP-11 à CAP-13)

Il est conservé sur le disque avec le lot, dans `var/sorties/<id>/`, et survit à l'arrêt du serveur. Pour chaque fiche :

| Donnée | Contenu |
|---|---|
| Fiche générée | Sortie des garde-fous, conservée telle quelle, avec ses motifs (affichés « signalé à la génération ») |
| Fiche corrigée | Titre, description, impact, recommandation, vecteur CVSS (score et sévérité recalculés par le code), références restantes, qui sont un sous-ensemble de celles de la fiche générée |
| Candidat choisi | L'identifiant du constat type retenu parmi les 3 candidats (fiche) ou dans tout le catalogue (entrée `non_rattachee`). Le changer remplace la fiche générée et efface la fiche corrigée, après confirmation si la fiche porte des corrections ou est validée |
| Modèle de génération | Le modèle qui a produit la fiche générée (celui du lot, ou de la régénération) |
| Statut de relecture | `a_valider` ou `validee`. Toute modification enregistrée d'une fiche validée la repasse `a_valider` |

Une entrée `non_rattachee` dont on choisit un constat dans la liste filtrable du catalogue devient une fiche avec cet état. La régénération utilise le modèle retenu au lancement du lot ; une entrée d'un lot v0.1.0 (sans note source enregistrée) se relit, se corrige et s'exporte, mais ne se régénère pas. Le statut de génération (`ok` / `a_revoir`) et le statut de relecture sont indépendants.

Le lot consigne aussi son workflow, sa langue, sa date de création et le processus qui l'exécute. Tant que ce processus vit et que le lot n'est pas terminé, le lot est « en cours » : l'UI le montre en lecture seule et la CLI refuse de l'exporter.

Un lot échoué garde les fiches déjà produites relisibles et exportables ; les notes non traitées au moment de l'échec sont listées comme telles, distinctes des entrées `non_rattachee`. Relancer les notes non traitées (ou toute note) crée un nouveau lot ; les corrections et validations du lot d'origine ne sont pas modifiées.

## Exports Word (CAP-13, CAP-17)

| Export | Fichier | Fiches incluses | Marque |
|---|---|---|---|
| Final | `rapport-<id_lot>.docx` | Fiches `validee` seulement, dans leur version corrigée ; les fiches non validées sont listées en annexe (statut « Non validée », `en` : « Not validated ») | aucune ; statut « Validée » (`en` : « Validated ») sans les motifs de génération |
| Brouillon | `brouillon-<id_lot>.docx` | Toutes les fiches, chacune dans sa version courante | « Non validée » (`en` : « Not validated ») dans l'en-tête de chaque fiche `a_valider` |

Les deux exports suivent la structure de contrats §17 et l'annexe des notes écartées. Avant l'export final, l'UI demande confirmation s'il reste des fiches non validées ; la CLI en affiche le nombre. Disponibles aussi en CLI (`waveaudit exporter <lot> [--brouillon]`) ; la validation des fiches reste UI seule.

## Libellés Word par langue (CAP-8)

Les libellés français sont ceux de contrats §17. Les libellés anglais sont adoptés (Anaël, 2026-10-18).

| fr (contrats §17) | en |
|---|---|
| Démonstration — données fictives | Demonstration — fictitious data |
| Rapport de constats | Findings report |
| N° / Titre / Sévérité / Score / Statut | No. / Title / Severity / Score / Status |
| Description / Impact / Recommandation | Description / Impact / Recommendation |
| CVSS 3.1 / Références / Statut / Traçabilité | CVSS 3.1 / References / Status / Traceability |
| Aucune / Faible / Moyenne / Élevée / Critique | None / Low / Medium / High / Critical |
| OK / À revoir | OK / To review |
| Annexe — notes écartées / Note / Statut / Motif | Appendix — excluded notes / Note / Status / Reason |
| Non validée / fiche non validée, exclue du rapport final | Not validated / not validated, excluded from the final report |
