---
id: W3b
title: Écran de relecture (tiroir, candidats, fiche, exports)
status: review
sources:
  - ../stories.yaml
  - ../SPEC.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/impacts-v2.md
  - ../../../planning-artifacts/ux/EXPERIENCE.md
  - ../../../planning-artifacts/ux/DESIGN.md
  - story-W3a-api-relecture.md
---

# Story W3b — Écran de relecture (tiroir, candidats, fiche, exports)

## Livré

`templates/lot.html` (remplacé), `static/relecture.js` (nouveau, remplace `etat.js` sur cette
page), `static/style.css` (ajouts en fin de fichier). Aucune route nouvelle, aucune route de
page modifiée (`pages.py` non touché) : la langue affichée sur le panneau note et le formulaire
est lue côté client (`GET /lots/{id}/relecture`), pas passée par le gabarit.

`lot.html` garde la section de suivi (`#suivi`, barre + journal, identique à `etat.js`) puis
affiche `#relecture` (tiroir, candidats ou catalogue, fiche, export) dès que le lot n'est plus
`en_cours`, y compris `echoue` et `interrompu` (EXPERIENCE « State Patterns » : les fiches déjà
produites restent relisibles et exportables). Trois dialogues statiques (`role="alertdialog"`,
`aria-modal="true"`, `aria-labelledby`) : changement de candidat sur fiche corrigée ou validée,
conflit de version, export final avec fiches non validées.

`relecture.js` couvre, par-dessus l'API de W3a :

- tiroir (`listbox`/`option`, flèches + Entrée/Espace, repli par classe `tiroir-repli`, pas
  `[hidden]`) ;
- barre des candidats (`tablist`/`tab` statiques × 3, un seul `tabpanel` partagé) pour une
  entrée `fiche` ou `ecartee` rattachable, liste filtrable du catalogue (label + champ de
  filtre) pour une entrée `non_rattachee` ;
- formulaire de fiche à enregistrement automatique (anti-rebond 800 ms, corps complet, un seul
  `PUT` en vol par entrée, dernier corps en file, `version` du serveur reprise à chaque réponse) ;
  conflit 409 → dialogue « Garder ma version » / « Recharger » ; 503 ou erreur réseau → nouvelle
  tentative après 3 s, saisie conservée ;
- CVSS : aperçu de sévérité calculé localement (jamais envoyé), `aria-invalid` et message sous
  le champ si le vecteur est invalide ;
- validation (`Ctrl+Entrée` ou bouton, désactivé si CVSS invalide, raison liée par
  `aria-describedby`), navigation (`Ctrl+Alt+↓`/`↑` hors d'un champ de formulaire, boutons
  Suivante/Précédente toujours actifs) ;
- changement de candidat : file d'enregistrement vidée avant l'appel, confirmation si la fiche
  est corrigée ou validée (et sur 409 `confirmation_requise` du serveur), sondage de l'entrée
  jusqu'à `generation != "en_cours"` ;
- export final (confirmation si `non_validees > 0`) et brouillon, réponse `Blob` + lien
  `download` (URL `blob:`), sans passer par un GET ;
- jeton CSRF relu sur 403 `csrf_invalide` via `WaveAudit.envoyer` (inchangé, `commun.js`) ;
- dialogues fermables par `Échap`, focus initial sur le bouton « annuler », focus rendu à
  l'élément déclencheur à la fermeture.

`style.css` : disposition de la relecture (tiroir, note, fiche), pastilles CVSS, encart des
motifs, barre d'actions, dialogues. **Écart au design** : les superpositions de dialogue et
l'ombre de boîte de DESIGN.md sont en `rgba(...)` (non déclarées dans `tokens.css`/`colors` de
DESIGN.md) ; `tests/unitaires/test_contraste.py::test_style_css_sans_couleur_litterale` interdit
toute couleur littérale hors tokens. Rendues en couleur pleine (`var(--couleur-encre)` pour la
superposition, `border: 1px solid var(--couleur-trait)` à la place de l'ombre) : visuellement
plus opaque/plat que prévu par DESIGN.md. Signalé pour une éventuelle story de token dédié
(superposition/élévation), pas rouvert ici.

## Tests

- `tests/e2e/test_ui.py` et `tests/e2e/test_incident_ui.py` : verts sans modification
  (`test_aucune_url_externe_dans_templates_et_static`, bandeau, CSP, accessibilité accueil et
  suivi, incident).
- `tests/e2e/test_relecture_ui.py` (ajoutés, API W3a inchangée) :
  `test_accessibilite_relecture`, `test_tiroir_listbox_et_barre_candidats_tablist`,
  `test_liste_du_catalogue_avec_libelle_et_filtre`,
  `test_dialogues_de_confirmation_et_export_final`, `test_lang_sur_panneau_note_et_formulaire`,
  `test_aucun_attribut_on_ou_style_en_ligne_sur_la_page_de_relecture`.
- `tests/unitaires/test_contraste.py` : vert après le remplacement des `rgba()` (ci-dessus).

## Écarts et points REC (JS non exécuté par les tests)

- Le `lang` du panneau note et du formulaire est posé statiquement à `fr` par le gabarit et mis
  à jour par `relecture.js` à l'ouverture (`etat.langue`) : à vérifier en REC sur un lot anglais.
- Parcours clavier complet (flèches du tiroir, onglets, raccourcis `Ctrl+Entrée` /
  `Ctrl+Alt+↓↑`, fermeture `Échap` avec retour du focus), anti-rebond visuel (« Enregistrement… »
  → « Enregistré »), confirmation de changement de candidat et d'export final, repli du tiroir
  sous 1440px : à dérouler en REC dans un vrai navigateur.
- Superpositions de dialogue opaques (écart de design ci-dessus) : à confirmer visuellement.
