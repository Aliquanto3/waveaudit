"""Jeu de démonstration CERT et son oracle (contrats §21, formats-incident.md, C2).

Ne vérifie que ce qui relève de la lecture (CAP-1) : les lignes illisibles et le nombre
d'événements lus. Les détections et indicateurs de l'oracle sont calibrés par C5.
"""

from datetime import datetime
from pathlib import Path

import yaml

from waveaudit.adaptateurs.journaux import SourceJournauxFichiers
from waveaudit.adaptateurs.regles_yaml import CatalogueReglesYaml
from waveaudit.domaine.detection import detecter
from waveaudit.domaine.indicateurs import extraire

RACINE = Path(__file__).parents[2]
DOSSIER_DEMO = RACINE / "donnees" / "demo" / "incident"
ORACLE = yaml.safe_load(
    (RACINE / "donnees" / "demo" / "incident-attendu.yaml").read_text(encoding="utf-8")
)


def test_lecture_de_la_demo():
    lecture = SourceJournauxFichiers(decalage_syslog=ORACLE["decalage_syslog"]).lire(
        DOSSIER_DEMO, annee=ORACLE["annee"]
    )
    ignorees = sorted((i.fichier, i.ligne) for i in lecture.ignorees)
    attendues = sorted((i["fichier"], i["ligne"]) for i in ORACLE["ignorees"])
    assert ignorees == attendues
    assert len(lecture.evenements) >= 80


def test_fichiers_de_demo_en_lf():
    """Revue C2 : `sysmon.csv` avait été commité en `\\r\\r\\n` (origines doublées)."""
    for chemin in DOSSIER_DEMO.iterdir():
        assert b"\r" not in chemin.read_bytes(), chemin.name


def test_oracle_egal_au_pipeline_reel():
    """Lecture -> detecter -> extraire (code de main) donne exactement l'oracle écrit à la main.

    L'oracle reste calculé à la main (formats-incident.md) : ce test ne le génère pas, il le
    confronte au moteur. Une divergence se corrige dans l'oracle ou dans le code, motif cité.
    """
    lecture = SourceJournauxFichiers(decalage_syslog=ORACLE["decalage_syslog"]).lire(
        DOSSIER_DEMO, annee=ORACLE["annee"]
    )
    regles = CatalogueReglesYaml(RACINE / "donnees" / "regles").regles()
    detections = detecter(regles, lecture.evenements)
    assert [(d.regle_id, d.debut, d.fin, d.hotes, len(d.evenements)) for d in detections] == [
        (
            a["regle_id"],
            datetime.fromisoformat(a["debut"]),
            datetime.fromisoformat(a["fin"]),
            a["hotes"],
            a["nb_evenements"],
        )
        for a in ORACLE["detections"]
    ]
    union = {e.cle: e for d in detections for e in d.evenements}
    assert [i.model_dump() for i in extraire(list(union.values()))] == ORACLE["indicateurs"]
    benins = len(lecture.evenements) - len(union)
    assert benins / len(lecture.evenements) >= ORACLE["min_part_benigne"]


def test_oracle_ne_contient_aucune_valeur_reservee_au_faux_moteur():
    texte = (RACINE / "donnees" / "demo" / "incident-attendu.yaml").read_text(encoding="utf-8")
    for valeur in ("203.0.113.254", "0f" * 32, "T9999", "T1110.999"):
        assert valeur not in texte
