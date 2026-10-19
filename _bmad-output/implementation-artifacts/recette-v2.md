# Recette v2 (REC) — fiche à remplir

Poste : EliteBook (i5-1145G7, 15,7 Gio). Base : `main` à a49d271 (suite 1079 verts, `slow` 5/5, CI verte).
Déroulé détaillé : `docs/guide-testeurs.md` (parcours de Camille et Karim). Version interactive : https://claude.ai/artifact/Nk48VmdCwE7XfDNTGvUuWQ.
Cocher `[x]` si conforme, `[!]` si écart (le décrire dans « Écarts relevés »).

## 0. Avant de commencer

- [ ] Fermer les applications lourdes ; RAM libre notée : ____ Go (7,7 Go au moment de la préparation).
- [ ] `tasklist | findstr llama-server` : aucune ligne.
- [ ] `uv run waveaudit version` affiche 0.2.0rc1 (version candidate ; la 0.2.0 n'est posée qu'après la recette).
- [ ] `uv run waveaudit ui`, puis ouvrir `http://127.0.0.1:8765` dans un vrai navigateur (Edge ou Firefox).

Dossiers prêts (ignorés par git) :
- `var/recette-v2/notes/` : les 6 notes du banc (01, 11, 16, 22, 26, 29) et `99-hors-sujet.md` (recette de cuisine, pour l'entrée non rattachée).
- `donnees/demo/incident/` : les 5 journaux de la démo CERT.
- `var/recette-v2/incident-refus/notes.txt` : fichier non reconnu comme journal.

## 1. Parcours de Camille (critère de succès de la SPEC)

Accueil : workflow « Fiches », granite (défaut), langue « Français », dépôt des 7 fichiers de `var/recette-v2/notes/`.

- [ ] Le lot démarre ; progression et journal visibles ; durée par fiche notée : ____ s (banc : ~28 s).
- [ ] À la fin du lot, l'écran de relecture s'ouvre seul (note à gauche, fiche à droite, tiroir de 7 entrées).
- [ ] `99-hors-sujet` ressort **non rattachée**, sans génération automatique.
- [ ] Sur `99-hors-sujet` : filtrer le catalogue, choisir un constat à la main → la fiche se génère.
- [ ] Changement de candidat sur une autre entrée (flèches, `Entrée`/`Espace`) → « Génération en cours » puis nouveau texte.
- [ ] Correction d'un champ d'une troisième fiche → « Enregistrement… » puis « Enregistré ».
- [ ] Changement de candidat sur une fiche déjà corrigée ou validée → confirmation demandée.
- [ ] Validation au clavier (`Ctrl+Entrée`) et navigation (`Ctrl+Alt+↓`/`↑`) ; fiches validées repérées dans le tiroir.
- [ ] « Exporter un brouillon » avant la dernière validation → `.docx` immédiat, fiche non validée marquée.
- [ ] Export final avec une fiche non validée → confirmation demandée.
- [ ] Toutes validées, « Exporter » → rapport final sans confirmation ; ouvert dans Word, table de synthèse correcte.
- [ ] Le thème (palette, focus visible) est cohérent sur l'accueil, le suivi et la relecture.

## 2. Parcours de Karim (démo CERT dans l'UI)

- [ ] Bascule « Fiches » / « Incident » à l'accueil (pas de choix de langue en incident).
- [ ] Dépôt des 5 fichiers de `donnees/demo/incident/` → le lot démarre et se termine.
- [ ] Résumé par sévérité, carte « Critique » → liste filtrée.
- [ ] « Télécharger le rapport » → `.docx` immédiat, lisible dans Word.
- [ ] Dépôt de `var/recette-v2/incident-refus/notes.txt` → refus `aucun_journal_reconnu`, aucun lot créé.

## 3. Points navigateur et accessibilité

- [ ] Tiroir : flèches ; onglets de candidats ; `Échap` ferme un dialogue et rend le focus au bouton d'origine.
- [ ] Piège de focus dans un dialogue ouvert (Tab / Maj+Tab bouclent).
- [ ] Dialogues de confirmation et de conflit **opaques** (écart W3b à confirmer : fond opaque au lieu de l'ombre rgba de DESIGN.md).
- [ ] Repli du tiroir sous 1440 px de large.
- [ ] Annonces `aria-live` lues par le lecteur d'écran (Narrateur : `Ctrl+Win+Entrée`).
- [ ] Deux onglets sur la même fiche : correction dans les deux → dialogue de conflit sur le second ; `Échap`, « Garder ma version », « Recharger ».
- [ ] Serveur arrêté pendant un enregistrement → message de réessai ; reprise au redémarrage.
- [ ] Lien « Télécharger le rapport » sur l'écran de suivi dès la fin du lot.

## 4. Lot en anglais et relecture de Q3

Relancer le parcours sur 3 ou 4 notes avec la langue « English » (ou `uv run waveaudit fiches var/recette-v2/notes --langue en`).

- [ ] `lang` du panneau de relecture passe à `en`.
- [ ] Word final `en` : libellés des statuts et motifs en anglais dans l'annexe des écartées (story LIB) ; aucun code brut français dans le final.
- [ ] Relecture des 10 constats traduits (textes `en` dans `donnees/catalogue/*.yaml`), sans contresens :
  - [ ] AD-KERBEROASTING
  - [ ] AD-ADCS-ESC1
  - [ ] AUTRE-MFA-ABSENTE
  - [ ] CONFIG-DEBUG-ACTIF
  - [ ] CONFIG-CORS-DEBUG
  - [ ] CRYPTO-HACHAGE-FAIBLE
  - [ ] INFRA-IPMI-EXPOSE
  - [ ] INFRA-LLMNR-NBTNS
  - [ ] WEB-XSS-REFLECHI
  - [ ] WEB-SSTI

## 5. Robustesse

- [ ] Ctrl+C sur l'UI pendant un lot en cours ; arrêt en moins de ~10 s ; `tasklist | findstr llama-server` : aucune ligne (story ARR).
- [ ] Repli `qwen3.5-0.8b` avec peu de RAM (ouvrir la suite bureautique et d'autres applis jusqu'à passer sous le seuil `ram_min_defaut_go = 4.5` de `config/waveaudit.toml`, recharger l'accueil, puis lancer un lot) : `qwen3.5-0.8b` est présélectionné dans la liste « Modèle » et le lot aboutit. Aucun message n'annonce le repli (constat de la revue DOC-T) : dire si c'est gênant. RAM libre au lancement : ____ Go.
- [ ] Facultatif : un lot avec qwen3-1.7b (candidat) choisi à l'accueil, durée par fiche : ____ s.

## Écarts relevés

| # | Section | Constat | Gravité (bloquant / à corriger / accepté) | Suite |
|---|---|---|---|---|
| | | | | |

## Décision

- [ ] Recette concluante → version 0.2.0 : `version` dans `pyproject.toml`, tag annoté `v0.2.0`, release GitHub (notes tirées de `etat-v2.md`, « Bilan »), topic `status-*` mis à jour. Uniquement après l'accord d'Anaël.
- [ ] Recette non concluante → stories de correction listées ci-dessus, nouvelle REC partielle sur les points concernés.
