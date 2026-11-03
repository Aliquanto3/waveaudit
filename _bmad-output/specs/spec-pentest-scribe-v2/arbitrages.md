# Arbitrages de cadrage v2 (Anaël, 2026-10-18)

Base : v0.1.0 (tag `v0.1.0`), etat-de-nuit.md, bilan-modeles.md, validation-moteur.md.

## a. Écarts au contrat (contrats.md)

**Entérinés tels quels** (le contrat s'aligne sur le code) :
- §22 : champ facultatif `reflexion` par entrée du manifeste, transmis en `chat_template_kwargs={"enable_thinking": false}` (V1).
- §21 : neutralisation du point final avant les motifs (copie de même longueur ; point suivi d'un blanc, d'une ponctuation fermante ou séparatrice, ou de la fin ; jamais devant un chiffre) (C1, C4).
- §20 : `pic_rss_total_o` = maximum de la somme application + moteur au même échantillon (15).
- §18 : `Host: [::1]:<port>` accepté ; `/lots/{id}/etat?depuis=N` facultatif (14).
- §7 : œ, æ, ß remplacés (oe, ae, ss) avant NFKD (2).
- §3 : enveloppe 200 non conforme (corps non JSON, `choices` vide, `message` absent) → `MoteurInjoignable` ; `SortieInvalide` pour un `content` null ou non textuel (6).
- §17 : thème privé invalide → `ConfigurationInvalide` (code 2) à la construction de l'export (9).
- Signatures : `composition.ouvrir(..., *, id_lot=None)`, `ouvrir_moteur_incident(..., *, id_lot=None)`, `ExporteurIncidentDocx(max_preuves=…)`, `assembler_rapport(lecture, recits, regles)` (12, C1, C6a, C5).
- §12 : `sendto` et `sendmsg` (UDP) gardés aussi (7).
- CLI : `--modele` inconnu vérifié contre le manifeste (code 2) ; chemins absolus retirés des messages d'erreur (C6b).

**Corrigés par une story v2** :
- §5 : la nouvelle tentative sur `SortieInvalide` passe une seed différente (seed + 1). Touche le port `Moteur` (socle AD-0) : story de socle dédiée.
- §8 : `</note>` (et `</constat>`) échappés dans le corps et l'actif de la note.
- §6 : seuil de 5 caractères pour le titre, 20 pour les autres rubriques ; une URL présente dans la note (actif compris) n'est plus retirée ; garde-fou de répétition : sortie dégénérée → `a_revoir` (nouveau motif).
- C5 : noms privés de `lot.py` (`_ID_LOT`, `_Emetteur`, `_sans_chemin`, `_sorties`) rendus publics (story de socle).

## b. Fonctionnalités v2

- **Relecture et édition dans l'UI** : fiche à côté de sa note et de ses 3 constats candidats ; changer de candidat (relance la fiche) ; corriger le texte ; valider ; exporter en Word les fiches validées. Rouvre le non-goal POC l.77.
- **Workflow incident dans l'UI** (dépôt des journaux, suivi, rapport) et **choix du modèle** parmi les modèles installés. Rouvre le non-goal CERT l.53.
- **Fiches en anglais** : langue du rapport au choix ; catalogue bilingue, consigne par langue, libellés Word. Rouvre le non-goal POC l.75.
- Hors v2 : imports Burp et Nessus, EVTX (v3) ; workflows scripts et défense (rouvriraient les décisions 4 et 8 du forge : `bmad-correct-course`).

## c. Qualité, avant l'UI

- **Rattachement** des notes 01 et 29 : mots du catalogue et pondération BM25, mesurés sur les notes 21 à 30 non vues ; le choix du candidat dans l'UI sert de filet.
- **Recopie** : `repeat_penalty` exposé dans `[moteur]` et `moteur_openai`, garde-fou de répétition, rebanc de la consigne de l'essai 3 sur un lot complet (granite et qwen3-1.7b). Objectif : recopie < 0,7 sans baisse du taux ok.
- **Repli** : qwen3.5-0.8b remplace MiniCPM5 ; garde-fou de langue (fiche ou récit hors de la langue demandée → `a_revoir`).
- **Défaut** : granite jusqu'au rebanc. qwen3-1.7b passe défaut s'il atteint ≥ 5/6 ok, une recopie < 0,6 et une médiane < 40 s sur l'EliteBook.

## Cadrage rouvert

Non-goals de spec seulement (POC l.75 et l.77, CERT l.53) : notés dans la spec v2, pas de `bmad-correct-course`. Aucune décision verrouillée du forge n'est rouverte.
