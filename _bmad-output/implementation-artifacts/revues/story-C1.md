# Revue — story C1 (Extension du socle pour le CERT)

Branche revue : `story-C1-revue` (depuis `story-C1` a3e559d, rebase sur `main` 81c4ea8 sans
conflit). Écart accepté : `ouvrir_moteur_incident(config, modele, *, id_lot=None)`.

## Revue

- medium — second avis — reporté (C4) : les motifs normatifs §21 (`(?![\d.])`) ratent un jeton
  suivi d'un point final (« T9999. », « 203.0.113.254. » → aucun jeton ; « 2001:db8::1. » →
  candidat invalide laissé tel quel). Une référence ou IP inventée en fin de phrase survivrait
  aux garde-fous (CAP-5). §21 ne prévoit aucun retrait de ponctuation pour ces jetons (seul §6
  le fait pour les URL MVP). Motifs non modifiés ; comportement figé par
  `test_motifs_point_final_comportement_fige` ; traitement proposé pour C4 (décision à
  consigner dans contrats §21) dans la spec de la story, section Reports.
- info — reviewer — vérifié : `JournalLot` en cas d'exception : `__exit__` ferme, l'exception
  remonte, `lot_echoue` reste écrit avant la fermeture ; comportement identique à l'ancien
  `with open(...)`.
- info — reviewer — vérifié : faux moteur en mode incident (`<constat>` d'abord, puis `<regle>`,
  sinon `SANS_CONSTAT` ; `erreur_500`, `json_invalide*`, `lent` traités avant et donc valables
  en mode incident ; `SCENARIOS` inchangé).
- low — reviewer — rejeté : `decalage_syslog` accepte `+99:99` (seul le motif est au contrat).
- Complexité : 0 constat.

## Vérifications

413 tests verts avant correction, 414 après ; ruff check et format verts. Motifs exécutés sur
les trois cas du second avis (résultats ci-dessus confirmés).

## Verdict

Prête à intégrer. Report : point final et motifs, à trancher avant C4.
