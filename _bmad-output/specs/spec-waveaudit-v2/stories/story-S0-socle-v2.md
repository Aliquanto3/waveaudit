---
id: S0
title: Socle v2 (formes partagées, configuration, ports, faux moteur, noms publics de lot.py)
status: review
sources:
  - ../stories.yaml
  - ../SPEC.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/impacts-v2.md
---

# Story S0 — Socle v2

## Livré

- `domaine/modeles.py` : `Langue`, `LANGUES`, `TextesConstat` (4 textes non vides),
  `ConstatType.en` (facultatif) et `textes(langue)` (`ValueError` si `en` vaut `None`),
  `CodeMotif` `repetition`, `langue`, `lot_interrompu`, `RequeteLot.langue` (`None`).
- `domaine/configuration.py` et `config/waveaudit.toml` ensemble : `moteur.repeat_penalty`
  (0 à 2, défaut 0.0), `[fiches] langue` (`ConfigFiches`, défaut `fr`),
  `ui.inactivite_moteur_s` (> 0, défaut 300).
- `domaine/ports.py` : `Moteur.generer_json(..., seed=None)`, `OptionsExport` (dataclass
  figée, commentaire de `non_validees` : annexe en final), `Exporteur.exporter(..., options)`.
- `domaine/relecture.py` (nouveau) : `FicheCorrigee`, `EntreeRelecture`, `EtatRelecture`,
  `RefusRelecture(code, message)` et les invariants du §25. Aucune règle pure (c'est R1).
- `config/artefacts.toml` : ordre moteur, défaut, repli, candidats ; `qwen3.5-0.8b-q4km`
  `modele_repli`, `minicpm5-1b-q4km` `candidat` ; `duree_indicative_s` de bilan-modeles.md
  (17,1 ; 11,4 ; 12,9 ; 20,4). `installation/manifeste.py` : `Artefact.repeat_penalty`
  (0 < x <= 2) et `duree_indicative_s`.
- `tests/faux_moteur.py` : scénarios `repetition`, `langue_anglaise`, `langue_francaise`,
  `ecriture_etrangere`, `url_de_la_note` (modes fiche et incident).
- `application/lot.py` : `MOTIF_ID_LOT` (64 caractères au plus), `Emetteur`, `sans_chemin`,
  `dossier_sorties`, `verifier_id_lot` (crée le dossier), `dossier_lot_existant` (aucun
  mkdir). `application/incident.py` : imports publics, `_id_lot` dupliqué supprimé.
  `interfaces/cli.py` : import de `sans_chemin`.
- Tests réalignés : `e2e/test_lot.py` (`lot.sans_chemin`), commentaire de
  `e2e/test_incident.py`, `u/test_config.py::test_manifeste_artefacts`,
  `u/test_composition.py::test_local_gere_demarre_llama_server` (RAM 2 Go : qwen3.5).
- Tests nouveaux : `u/test_modeles.py`, `u/test_config.py`, `u/test_relecture_modeles.py`,
  `u/test_faux_moteur.py`, `u/test_lot_noms.py`, `u/test_architecture.py` (aucun nom `_…`
  de `waveaudit.application.lot` importé ou lu hors de `lot.py`, `tests/` compris).

Seul changement de comportement : le repli quand la RAM est basse passe à qwen3.5-0.8b (et
`waveaudit installer` télécharge qwen3.5 au lieu de MiniCPM5). `MOTIF_ID_LOT` refuse
désormais un id de plus de 64 caractères (revue A3).

## Choix d'interprétation

- Invariant « `etat == "fiche"` ⇔ `fiche_generee` et `statut_relecture` renseignés » appliqué
  champ par champ : hors de l'état `fiche`, les deux valent `None`.
- `candidat_choisi` hors `candidats` toléré seulement pour une entrée `fiche` dont aucun
  candidat n'a un score > 0 (définition de `non_rattachee`, §5 étape 2) : après
  `remplacer_fiche`, `ecartee` vaut `None` et l'origine ne se lit plus autrement.
- `EtatRelecture.entrees` : index strictement croissants (validateur).
- Noms réservés Windows refusés explicitement (`CON`, `PRN`, `AUX`, `NUL`, `COM0-9`,
  `LPT0-9`) par `verifier_id_lot` et `dossier_lot_existant`, en plus du contrôle `is_dir`.
- Faux moteur : `url_de_la_note` ne modifie rien en mode incident (pas de `<note>`) ;
  `repetition` vise `recit` en incident, avec le `maxLength` de `recit`.
- `OptionsExport()` en valeur par défaut du protocole : `# noqa: B008` (dataclass figée),
  `pyproject.toml` inchangé.

## Reports

- README, tableau des modèles (l. 183) : le repli y est encore MiniCPM5. À réaligner par
  la story DOC.
- La transmission de `seed` et de `repeat_penalty` par `MoteurOpenAI` et
  `composition._moteur` reste à Q1 ; `ExportDocx.exporter` n'accepte pas encore `options`
  (story d'export, §27) : le protocole est en avance sur les adaptateurs, sans effet à l'exécution.

## Revue

Revue unique consignée dans `_bmad-output/implementation-artifacts/revues/story-S0.md` : 5 constats du second avis (low, 4 rejetés, 1 reporté à DOC), 2 du reviewer (low, 1 corrigé dans `test_architecture.py`, 1 laissé) ; complexité : 0 constat.
