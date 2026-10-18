# Écarts au contrat (CAP-16)

Décisions d'Anaël du 2026-10-18. L'architecture les consigne dans `contrats.md`.

## Entérinés (le contrat s'aligne sur le code v0.1.0)

| Section | Écart |
|---|---|
| §22 | Champ facultatif `reflexion` par entrée du manifeste, transmis en `chat_template_kwargs={"enable_thinking": false}` |
| §21 | Neutralisation du point final avant les motifs : copie de même longueur ; s'applique au point suivi d'un blanc, d'une ponctuation fermante ou séparatrice, ou de la fin, jamais à un point devant un chiffre |
| §20 | `pic_rss_total_o` = maximum, sur les échantillons, de la somme application + moteur au même instant |
| §18 | `Host: [::1]:<port>` accepté ; `/lots/{id}/etat?depuis=N` facultatif |
| §7 | œ, æ, ß remplacés par oe, ae, ss avant NFKD |
| §3 | Enveloppe 200 non conforme (corps non JSON, `choices` vide, `message` absent) → `MoteurInjoignable` ; `content` null ou non textuel → `SortieInvalide` |
| §17 | Thème privé invalide → `ConfigurationInvalide` (code 2) à la construction de l'export |
| Signatures | `composition.ouvrir(..., *, id_lot=None)`, `ouvrir_moteur_incident(..., *, id_lot=None)`, `ExporteurIncidentDocx(max_preuves=…)`, `assembler_rapport(lecture, recits, regles)` |
| §12 | `sendto` et `sendmsg` (UDP) gardés aussi |
| CLI | `--modele` inconnu vérifié contre le manifeste (code 2) ; chemins absolus retirés des messages d'erreur |

## Corrigés par une story v2 (le code s'aligne sur le contrat amendé)

| Section | Changement | Capacité |
|---|---|---|
| §5 | Nouvelle tentative avec `seed + 1` (port `Moteur`, socle) | CAP-1 |
| §8 | `</note>` et `</constat>` échappés dans le corps et l'actif | CAP-2 |
| §6 | Seuils titre 5 / rubriques 20 ; URL de la note conservée ; motif de répétition | CAP-3 |
| C5 | `_ID_LOT`, `_Emetteur`, `_sans_chemin`, `_sorties` de `lot.py` rendus publics (socle) | CAP-16 |
