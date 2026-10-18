# Revue — story W3b (écran de relecture : tiroir, candidats, fiche, exports)

Commit relu : f1faf85 (base 205b590), branche `worktree-agent-a28d5fa75d62efb90`. ARR et LIB
avancés sur `main` : non touchés (pas de rebase). Fichiers revus : `static/relecture.js`,
`templates/lot.html`, `static/style.css`, `e2e/test_relecture_ui.py`. Gabarit, ARIA statique,
CSP, tokens CSS et noms des routes et champs de W3a conformes. Le JS, exécuté par aucun test,
portait l'essentiel des défauts : la file d'enregistrement était globale (index et version lus
au moment de l'envoi, pas de la saisie). `relecture.js` est réécrit autour d'un état par
entrée (`etatDe(index)` : version, envoi en vol, dernier corps en file, réessai, conflit,
rappels de fin de file).

Preuve : harnais Node `tests/js/harnais_relecture.js` (DOM, minuteries et réseau simulés, faux
serveur W3a), lancé par `unitaires/test_relecture_js.py` **seulement si `node` est sur le PATH**
(sauté en CI, aucune dépendance ajoutée). 18 scénarios, dont 17 échouent sur f1faf85 ; l'aperçu
CVSS est comparé à `cvss31.evaluer` sur les 2592 vecteurs de base (égalité exacte).

| Sévérité | Source | Constat | Décision |
|---|---|---|---|
| high | second avis 1 | Réponse d'un PUT en vol écrasait `courante` après un changement d'entrée : le PUT suivant partait vers l'index de l'ancienne entrée avec le corps de la nouvelle. | Corrigé : chaque envoi fige l'index et la version de son entrée (`st`) ; la réponse ne touche l'écran que si `st === ouverte`. Scénarios « 1/3 » et « 1 : Valider sur B ». |
| high | second avis 2 | Tout refus (422, 404, 409 `lot_en_cours_externe`…) relançait le même PUT toutes les 3 s, sans fin, sans `detail`. | Corrigé : réessai sur 503 et erreur réseau seulement, borné à 10 (puis message « modifiez un champ ou rechargez ») ; tout autre refus affiche `detail` et s'arrête, la saisie suivante repart. Scénarios « 2 », « 8 : réessai borné ». |
| medium | second avis 3 | `annulerAntiRebond()` dans `ouvrirEntree` et `lancerCandidat` perdait la saisie des 800 dernières ms (et le candidat partait sans confirmation). | Corrigé : `vider(st)` envoie la saisie en attente avant tout changement d'entrée (aussi au rendu, pour une frappe pendant la lecture de la suivante) ; le candidat attend la file puis décide sur l'entrée enregistrée. Scénario « 3 ». |
| medium | second avis 4 | Valider ou changer de candidat pendant un PUT en vol envoyait l'ancienne version (faux 409). | Corrigé : `apresFile(st, …)` attend la fin de la file (rappels un par un) puis lit `st.version`. Scénario « 4 ». |
| medium | second avis 5 | `nonValidees` lu au chargement seulement : compte faux dans le dialogue d'export. | Corrigé : recompté à chaque réponse d'écriture et relu (`GET …/relecture`) au clic sur « Exporter », après la file. Scénarios « 5 ». |
| medium | second avis 6 | Vecteur corrigé invalide : le champ remontrait le vecteur généré (`fiche_courante`), écrit au PUT suivant. | Corrigé côté JS : le champ montre `fiche_corrigee.cvss_vecteur` (état invalide, Valider désactivé). Domaine non touché (`fiche_courante` reste conforme à §25 [revue E30]). Scénario « 6 ». |
| medium | second avis 7 | Échap fermait le dialogue de conflit et la saisie suivante écrasait l'autre onglet. | Corrigé : Échap ferme sans choix, l'état `conflit` reste ; toute saisie, validation ou changement de candidat rouvre le dialogue, rien n'est écrit. « Garder ma version » renvoie la saisie à l'écran (la plus récente) avec la version du serveur. Scénarios « 7 », « Recharger ». |
| medium | second avis 8 | Réessai après 503 avec un corps périmé ; « Garder ma version » réécrivait l'ancien texte. | Corrigé : pendant l'attente du réessai les saisies vont en file, le réessai envoie la dernière. Scénario « 8 ». |
| medium | reviewer | 409 `confirmation_requise` du serveur relançait aussitôt avec `confirmer: true` : la confirmation était contournée. | Corrigé : le dialogue de confirmation s'ouvre. Scénario « confirmation_requise ». |
| medium | reviewer | Aperçu CVSS « grossier » (comptage de `:H`) : 9.8 affiché « Élevée », etc. (EXPERIENCE : score et sévérité recalculés à la frappe). | Corrigé : score de base CVSS 3.1 exact (formule FIRST, arrondi supérieur 3.1), métriques dans n'importe quel ordre comme `cvss31` ; égal au domaine sur les 2592 vecteurs. |
| medium | reviewer | Réponses de `GET …/entrees/{i}` dans le désordre (navigation rapide, sondage de génération) : une ancienne entrée pouvait s'afficher. | Corrigé : jeton d'affichage, seule la dernière ouverture demandée est rendue. Scénario « désordre ». |
| low | second avis 9 | `chargerListe` sans contrôle de `reponse.ok`. | Corrigé : `detail` affiché (409 `relecture_illisible`, 404). |
| low | second avis 10 | `generation == "echec"` et `erreur_generation` jamais affichés. | Corrigé : « La régénération a échoué : … » dans la zone de génération ; « Génération terminée. » annoncé à la fin. |
| low | second avis 11 | Pas de piège de focus dans les dialogues `aria-modal`. | Corrigé : Tab et Maj+Tab bouclent sur les boutons du dialogue ; aucun raccourci de page sous un dialogue. Scénario « 11 ». |
| low | second avis 12 | Lien « Télécharger le rapport » de W2 disparu ; `etat.js` orphelin. | Corrigé : `<a id="lien-rapport">` dans le gabarit (masqué, affiché par le JS quand le lot est terminé) ; `etat.js` supprimé (aucune référence). Test `e2e::test_lien_du_rapport_v010_sur_la_page_de_suivi`. |
| low | second avis 13 | Pas de `.catch` (liste, catalogue, export). | Corrigé : message « Le serveur ne répond pas… ». |
| low | reviewer | Onglets sans flèches gauche/droite (EXPERIENCE, APG Tabs) ; `tabpanel` toujours étiqueté par l'onglet 1 ; onglets tous à `tabindex=-1` possibles. | Corrigé : flèches entre onglets actifs, premier onglet actif dans l'ordre de tabulation, `aria-labelledby` sur l'onglet choisi ; tiroir avec `aria-activedescendant`. |
| low | reviewer | Bouton Valider non mis à jour à la frappe du CVSS ; `revokeObjectURL` juste après `click()` (téléchargement annulé par certains navigateurs). | Corrigé (mise à jour à la frappe ; révocation différée d'une seconde). |
| low | reviewer | `lang` du panneau note et du formulaire posé à `fr` par le gabarit, corrigé par le JS : le test n'exige qu'un `lang` non vide, pas la langue du lot. | Reporté : passer la langue par `pages.py` (lecture de `lot.json`), hors périmètre de la story ; vérifié en REC sur un lot anglais. |
| low | reviewer | L'aperçu n'accepte que les 8 métriques de base ; la bibliothèque `cvss` du serveur accepte aussi les métriques temporelles (Valider désactivé à tort pour un tel vecteur). | Accepté : saisie hors usage du POC ; le serveur reste l'autorité. |
| — | reviewer | Complexité : 1 constat. Chaque réponse d'écriture reconstruit le tiroir (O(n) en DOM). | Laissé : n ≤ 100 notes, une reconstruction par écriture, pas par frappe ; plus aucun sondage de `GET …/relecture` (chargement et export seulement), le sondage de `GET …/entrees/{i}` ne tourne que pendant une génération. |

Reste pour la REC (vrai navigateur) : parcours clavier complet (tiroir, onglets, `Ctrl+Entrée`,
`Ctrl+Alt+↓↑`, Échap et retour du focus, piège de Tab) ; indicateur « Enregistrement… » →
« Enregistré » et annonces `aria-live` au lecteur d'écran ; deux onglets sur la même fiche
(dialogue de conflit, Échap, « Garder ma version », « Recharger ») ; serveur arrêté pendant une
saisie (message de réessai, reprise) ; changement de candidat sur fiche corrigée (confirmation,
« Génération en cours », fin annoncée) ; export final avec fiches non validées et brouillon
(téléchargement par `Blob`) ; lien du rapport v0.1.0 ; `lang="en"` sur un lot anglais ;
superpositions de dialogue opaques (écart de design de la story) ; repli du tiroir sous 1440px.

Tests : `unitaires/test_relecture_js.py` (harnais Node, 18 scénarios) et le nouveau test du
lien verts ; `tests/e2e` et `tests/unitaires` 1073 verts ; ruff check et format propres.
