# Relecture adversariale du cadrage v2 (2026-10-18)

Contenu : diff `v0.1.0..e841c5e` sur spec-waveaudit-v2 et l'architecture (SPEC, formats, mesures-qualite, ecarts-contrat, stories.yaml, contrats.md, spine, impacts-v2.md). Lentilles : adversarial (A), edge-case-hunter (E) et verification-gap (V). Quand deux lentilles relèvent le même point, c'est un signal ; les renvois croisés figurent entre crochets.

## Adversarial (A)

### Sécurité web locale
- A1 §24/§26 : l'occupation est prise avant `nouvel_id_lot`, alors que `Occupation.id_lot` est obligatoire. Fixer l'ordre : créer l'id puis prendre le verrou (suppression du dossier si refus), ou occupation provisoire puis `definir`.
- A2 §26/§30 : course sur le 303 de l'incident. `lot.json` est écrit dans le fil de travail, donc `GET /incidents/{id}` le précède et la page redirige vers les fiches. Écrire `lot.json` de façon synchrone dans le POST, avant le 303.
- A3 §9/§26/§27 : `verifier_id_lot` fait `mkdir`, ce qui crée des lots fantômes à chaque GET et rend `lot_inconnu` intestable. Séparer `dossier_lot_existant` (sans effet de bord) ; borner l'id à 64 caractères.
- A4 §26 : des GET écrivent (export docx, réécriture « interrompue » avec version + 1) sans jeton CSRF, donc une `<img>` tierce déclenche une écriture et les versions provoquent des 409. Export en POST avec jeton, ou diffusion en flux sans écriture persistante ; état « interrompu » calculé à la lecture, sans écriture. [E26]
- A5 §26 : les limites par fichier, par nombre de fichiers et au total sont incompatibles (100 × 1 Mio > 20 Mio ; 50 × 10 Mio > 50 Mio). Aligner les trois règles et dire laquelle est dépassée. [E42]
- A6 §26 : un point ou une espace final dans le nom, et des doublons non normalisés, font que Windows écrase un fichier. Refuser `[. ]$` ; comparer les doublons après `rstrip(". ").casefold()` ; idem pour les notes. [E41]
- A7 §26 : `testserver` est accepté en production. Ne l'activer que par `creer_app(..., hotes_test=())` depuis les tests. [E27]

### Concurrence et persistance
- A8 §26 : l'enregistrement auto peut se mettre en conflit avec lui-même (PUT en vol) ; contradiction avec EXPERIENCE sur le 409. Au plus un PUT en vol, le dernier corps en file, renvoi avec la nouvelle version ; sur un vrai conflit, garder la saisie et proposer écraser ou recharger. [E23]
- A9 §25 : confirmation du changement de candidat, le disque et le navigateur divergent. Vider la file avant le POST, puis confirmer si une correction existe (disque ou en attente). [E24]
- A10 §24 : course entre la minuterie et `utiliser`/`fermer`. Verrou interne, compteur d'usages et annulation sous verrou ; test de concurrence dans M1. [E1]
- A11 §25/§9 : échec d'écriture de `relecture.json` (Defender, lecteurs) non spécifié. Décider (`lot_echoue` avec message), allonger les réessais, et tester avec un fichier tenu ouvert. [E14, E15]
- A12 §9/§25/§26 : relecture en 404 avant `initialiser` ou après un échec précoce. Si `lot.json` existe : 200 avec `entrees: []`. [E16]
- A13 §30 : un lot CLI en cours apparaît « interrompu » dans l'UI. Écrire le pid dans `lot.json` ; `en_cours` si le pid est vivant et le journal sans fin. [E12, E13]

### Fonctionnel et trous
- A14 §25/CAP-11 : les 3 candidats d'une entrée `non_rattachee` sont alphabétiques (scores nuls). Choix dans tout le catalogue, ou retirer la promesse. [E31]
- A15 §25 : régénération d'un lot v0.1.0 (`source=None`) ou modèle disparu. Refus `source_absente`, `generable=false` ; règle explicite si le modèle est absent. [E8]
- A16 §25 : le modèle de la régénération n'est pas tracé et peut changer selon la RAM. Utiliser `etat.modele` ou `EntreeRelecture.modele_generation`.
- A17 §25/§27 : le rapport final omet en silence les fiches non validées. Les lister en annexe ou afficher leur nombre.
- A18 stories Q2/L1 : CAP-4 (fiche française dans un lot `en`) n'est testé par aucune story. L'ajouter à L1.
- A19 §6 : le garde-fou de répétition fait des faux positifs sur des charges citées (`../`×5, `AAAA`, `%2e`). Exiger au moins une lettre et une longueur, ou exclure ce qui est cité depuis la note ; tests dédiés. [E37]
- A20 §6 : une URL n'est conservée que si elle figure en sous-chaîne, donc un préfixe d'URL passe. Comparer des jetons URL entiers. [E39]

### Contradictions et collisions
- A21 S0 contre §9 : les noms publics de `lot.py` diffèrent. Aligner S0 sur `MOTIF_ID_LOT`, `Emetteur`, `sans_chemin`, `dossier_sorties`, `verifier_id_lot`.
- A22 AD-18 : S0 est censée « ne changer aucun comportement », mais elle permute le modèle de repli. Reformuler AD-18 ou sortir la permutation de S0.
- A23 §2 contre AD-0/S0 : `config_test` doit changer, alors que `conftest.py` est déclaré inchangé. Trancher.
- A24 SPEC contre AD-18 : les exceptions au socle (Q4, Q5) manquent dans la SPEC.
- A25 SPEC « CI verte » contre spine « CI non requise » : une CI GitHub Actions existe pourtant (story D2). Corriger le spine.
- A26 formats.md : « titre inchangé » dans la traduction, alors que le titre est traduit. Écrire « identifiants ».
- A27 EXPERIENCE : les questions ouvertes sont tranchées par §24-§26, et le Flow 1 suppose la note 01 mal rattachée alors que CAP-5 la met au rang 1.
- A28 vagues 5 et 6 : collisions sur `test_composition.py` (Q5 et W2) et sur `app.py` (W3a et W4). Ordonner ces stories ou rendre les tests indépendants du défaut.

### Seuils
- A29 mesures-qualite contre §29 : deux définitions de la recopie (brut contre après garde-fous), et `autojunk` non fixé. Une seule définition, même réglage que la référence 0,93.
- A30 CAP-5 : la note 29 appartient à l'ensemble « non vu » tout en étant une cible du réglage, et le test bloquant pousse au surajustement. Retirer 29 de l'ensemble non vu ; 21-30 en xfail pendant Q4.
- A31 CAP-6 : « ok ≥ 6/6 » face aux nouveaux garde-fous ; une seule seed. Définir le critère ; 3 seeds.
- A32 §30 : la liste fermée des fichiers oublie les provisoires `.partiel`. [E20]

## Edge-case hunter (E)
- E1 minuterie expirée pendant `utiliser` [A10]. E2 `MoteurInjoignable` en régénération : garder la fiche, `generation="echec"`. E3 arrêt de l'application pendant une régénération : attendre ou annuler avant `fermer`. E4 exception de `regenerer` : `echec` avec message, verrou libéré. E5 « interrompue » écrase une régénération fraîche : relire sous verrou, à version égale. E6 fiche validée sans correction : confirmation aussi. E7 régénérer le candidat courant : refus `candidat_courant`. E8 `source=None` [A15]. E9 index des entrées reconstruites v0.1.0 : rang stable sur la réunion. E10 clé de réutilisation du moteur : nom résolu. E11 rôle `externe` : ne pas surcharger `modele_api` avec « externe ».
- E12-E13 lot CLI vu par l'UI, export CLI d'un lot UI en cours [A13]. E14-E15 écriture impossible : `lot_echoue` ; code 503 `ecriture_impossible` [A11]. E16 relecture en 404 [A12]. E17 `rapport_export` avec `source=None` lève `AttributeError`. E18 lot incident v0.1.0 sans `lot.json` : reconnu comme `lot_incident`. E19 deux exports simultanés : temporaire unique et verrou par cible. E20 provisoires [A32]. E21 index hors bornes : 404. E22 tri des lots : `cree_le` puis id.
- E23-E24 [A8, A9]. E25 jeton CSRF après redémarrage : sur 403, recharger le jeton et rejouer ; `Cache-Control: no-store` sur les pages. E26 GET à effet de bord [A4]. E27 `testserver` [A7]. E28 Host en casse différente ou port 80 omis : `lower()`.
- E29 références en double ou réordonnées : refus `reference_dupliquee`, ordre de la fiche générée. E30 vecteur corrigé invalide dans le brouillon : règle explicite. E31 [A14].
- E32 « 3DES » découpé en « des » (mot-outil fr), d'où un faux positif sur la note 16 en anglais : retirer `des` ou exiger des frontières sans chiffre. E33 sigles en capitales (IT, IS, TO) : les ignorer. E34 citation anglaise d'une note dans une rubrique française : exclure les segments cités. E35 lettres `Lm` et ordinales (nº, ʼ) : tolérées. E36 texte non latin cité depuis la note : ignoré. E37 [A19]. E38 titres identiques dans les deux langues (Kerberoasting) : liste d'exceptions.
- E39 [A20]. E40 `seed + 1` hors plage : borner la seed ou appliquer un modulo 2^32.
- E41 [A6]. E42 [A5].

## Verification gap (V)
- V1 CAP-6/CAP-7 : les seuils de recopie sont mesurés à la main, une fois ; aucun test de CI ne les garde. Assumé : vrai modèle hors CI. Au minimum, un test `slow` qui rejoue le banc sur 2 notes et vérifie un plafond.
- V2 CAP-15 : contraste et clavier vérifiés seulement à la main. Un test unitaire qui recalcule les ratios des paires de `tokens.css` contre DESIGN.md, et des tests E2E de focus et d'ARIA sur les gabarits.
- Vérifié : les tests nommés par impacts-v2.md et stories.yaml existent tous, avec des assertions exactes.

## Intégration (2026-10-18)

Décisions d'Anaël appliquées pour A13, A14, A17, A29-A31 ; le reste suit la correction proposée ou un choix technique noté. « C » = `contrats.md` (marques **[revue …]**), « S » = `SPEC.md`, « F » = `formats.md`, « M » = `mesures-qualite.md`, « X » = `EXPERIENCE.md`, « I » = `impacts-v2.md`, stories entre parenthèses. Bilan : 76 intégrés, 0 rejeté.

- A1 intégré : occupation provisoire puis `VerrouUnique.definir`, dossiers supprimés si refus après l'id (C §24, §26 ; M1, W2, W4).
- A2 intégré : `lot.ecrire_fiche_lot` appelé par la route avant le 303, idempotent pour les services (C §9, §26, §30 ; R2, W2, W4).
- A3 intégré : `dossier_lot_existant` sans `mkdir`, id ≤ 64 caractères (C §9, §26, §27 ; S0, W2, X2).
- A4 intégré : export en `POST` avec jeton, téléchargement par Blob ; génération interrompue calculée à la lecture (C §25, §26 ; R2, W3a, W3b).
- A5 intégré : trois limites explicites, 413 avec `limite`, 400 `trop_de_fichiers` (C §26, X ; W1).
- A6 intégré : noms terminés par `.` ou espace refusés, doublons après `rstrip(". ").casefold()` (C §26 ; W1, W4).
- A7 intégré : `creer_app(..., hotes_test=())`, `testserver` seulement depuis `web_outils` (C §26, spine AD-22 ; W1).
- A8 intégré : un PUT en vol, dernier corps en file, conflit avec « Garder ma version » / « Recharger » (C §26, X ; W3b).
- A9 intégré : file vidée avant le changement de candidat, confirmation selon l'entrée relue (C §26, X ; W3b).
- A10 intégré : verrou interne, compteur d'usages, test de concurrence (C §24 ; M1).
- A11 intégré : réessais 10 × 100 ms, `lot_echoue`, 503 `ecriture_impossible`, test fichier tenu ouvert (C §9, §25, §26 ; R2, W3a).
- A12 intégré : relecture vide (200, `entrees: []`) si `lot.json` existe (C §25, §26 ; R2, W3a).
- A13 intégré (décision Anaël) : `pid` dans `lot.json`, `processus_actif`, 409 `lot_en_cours_externe`, `exporter` code 2 (C §26, §27, §30, spine AD-20, S ; W2, X2, W3a).
- A14 intégré (décision Anaël) : liste filtrable du catalogue (`GET /lots/{id}/catalogue`) pour `non_rattachee`, `candidat_inconnu` selon l'entrée (C §25, §26, S CAP-11, F, X, prototype ; R2, W3a, W3b).
- A15 intégré : refus `source_absente`, `generable=false`, 422 `modele_indisponible` si le modèle a disparu (C §24, §25 ; R2, W3a).
- A16 intégré : modèle résolu du lot, `EntreeRelecture.modele_generation` (C §24, §25, F ; S0, R1, R2).
- A17 intégré (décision Anaël) : annexe des non validées en final, confirmation UI, nombre affiché par `exporter` (C §25, §26, §27, S CAP-13/17, F, X, prototype ; R1, X1, X2, W3a, W3b).
- A18 intégré : `test_pipeline_langue.py::test_fiche_francaise_dans_un_lot_en` (I l. 37 ; L1).
- A19 intégré : boucle retenue avec une lettre, 40 caractères et hors citation de la note (C §6 ; Q2).
- A20 intégré : URL comparées en jetons entiers (C §6 ; Q2).
- A21 intégré : S0 nomme `MOTIF_ID_LOT`, `Emetteur`, `sans_chemin`, `dossier_sorties`, `verifier_id_lot` (stories S0).
- A22 intégré : AD-18 nomme la permutation du repli comme seul changement de comportement de S0 (spine AD-18, S Constraints ; S0).
- A23 intégré : `conftest.py` reste inchangé (`config_test` relit le toml, vérifié) ; texte du §2 corrigé (C §2, spine AD-18 ; S0).
- A24 intégré : exceptions au socle (k1, b ; role, repeat_penalty, duree_indicative_s) dans la SPEC (S Constraints).
- A25 intégré : Deferred du spine corrigé (CI `.github/workflows/ci.yml`, D2) ; « CI verte » gardée dans la SPEC (spine).
- A26 intégré : « identifiants, références et URL inchangés, titre traduit » (S CAP-8, F ; Q3).
- A27 intégré : questions ouvertes closes avec renvois, Flow 1 générique (X).
- A28 intégré : W1 inclut les cinq routeurs, W3a/W4 sans `app.py` ; W2 dans `test_modeles_installes.py` ; X2 après W2 (spine AD-22, I, stories en-tête et vagues).
- A29 intégré (décision Anaël) : définition unique de la recopie, `autojunk` par défaut, replis à part (C §29, M, spine AD-23 ; B1).
- A30 intégré (décision Anaël) : notes non vues 21-28 et 30 (≥ 8/9, 9/9), `xfail` pendant Q4, valeurs dans le commit (C §29, S CAP-5, M ; Q4).
- A31 intégré (décision Anaël) : critère « ok ≥ 6/6 hors repetition et langue confirmés », 3 seeds, min et médiane, `banc --seed` (C §29, S CAP-6/7, M ; B1, Q5).
- A32 intégré : provisoires `.partiel` dans la liste fermée, test d'absence (C §30 ; R2, X2).
- E1 intégré : avec A10 (C §24 ; M1).
- E2 intégré : `repli_moteur` en régénération → `echec`, fiche gardée (C §25 ; R2).
- E3 intégré : lifespan attend l'usage en cours 10 s, puis lecture « interrompue » (C §24 ; W2).
- E4 intégré : toute exception de `regenerer` → `echec`, verrou libéré (C §25 ; R2).
- E5 intégré : plus d'écriture à la lecture (A4), donc plus d'écrasement (C §25 ; R2).
- E6 intégré : confirmation aussi pour une fiche validée (C §25, S CAP-11, X, prototype ; R2, W3b).
- E7 intégré : refus `candidat_courant` (C §25, §26 ; R2, W3a).
- E8 intégré : avec A15 (C §25 ; R2).
- E9 intégré : entrées v0.1.0 triées par note `casefold`, rang stable (C §25 ; R2).
- E10 intégré : clé de réutilisation = nom résolu (C §24 ; M1).
- E11 intégré : en externe, le lot et la régénération reçoivent `modele=None` (C §11, §26 ; W2, R2).
- E12 intégré : avec A13 (C §30 ; W2).
- E13 intégré : `exporter` refuse un lot en cours (C §27 ; X2).
- E14 intégré : avec A11 (C §9, §25 ; R2).
- E15 intégré : 503 `ecriture_impossible` (C §26 ; W3a).
- E16 intégré : avec A12 (C §25 ; R2).
- E17 intégré : `constat_attendu` `None` sans source (C §25 ; R1).
- E18 intégré : `lot_incident` selon la règle de `lots.py`, même sans `lot.json` (C §27 ; X2).
- E19 intégré : provisoire unique par export et verrou par cible (C §27 ; X1, X2).
- E20 intégré : avec A32 (C §30).
- E21 intégré : index hors bornes → 404 (C §26 ; W3a).
- E22 intégré : tri par `cree_le` puis id (C §30 ; W2).
- E23 intégré : avec A8 (C §26 ; W3b).
- E24 intégré : avec A9 (C §26 ; W3b).
- E25 intégré : `GET /api/jeton`, relecture du jeton sur 403, `no-store` sur le HTML (C §26, X ; W1, W3b).
- E26 intégré : avec A4 (C §26 ; W3a).
- E27 intégré : avec A7 (C §26 ; W1).
- E28 intégré : Host en minuscules, port 80 sans suffixe (C §26 ; W1).
- E29 intégré : refus `reference_dupliquee`, ordre de la fiche générée (C §25, §26 ; R1, W3a).
- E30 intégré : vecteur invalide enregistré tel quel, validation refusée, brouillon avec le CVSS généré (C §25 ; R1).
- E31 intégré : avec A14.
- E32 intégré : mots collés à un chiffre ignorés (`3DES`) (C §6 ; Q2).
- E33 intégré : sigles en capitales ignorés (C §6 ; Q2).
- E34 intégré : segments cités retirés avant comptage (C §6 ; Q2).
- E35 intégré : lettres `Lm` et ordinaux tolérés (C §6 ; Q2).
- E36 intégré : lettre non latine présente dans la note ou les preuves ignorée (C §6, §21 ; Q2).
- E37 intégré : avec A19.
- E38 intégré : `TITRES_IDENTIQUES_ADMIS` dans le test du catalogue (stories Q3).
- E39 intégré : avec A20.
- E40 intégré : `(seed + 1) % 2**32` (C §5 ; Q1).
- E41 intégré : avec A6.
- E42 intégré : avec A5.
- V1 intégré : `e2e/test_reel.py::test_banc_reel_deux_notes_plafond_recopie` (`slow`, plafond 0,8) (spine AD-23, M, I l. 34 ; Q5).
- V2 intégré : `tests/unitaires/test_contraste.py` et aide `tests/accessibilite.py` appliquée aux pages (C §28, S CAP-15, I l. 35-36 ; W5, W2, W4, W3b).
