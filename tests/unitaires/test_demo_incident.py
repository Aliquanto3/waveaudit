"""Jeu de démonstration CERT et son oracle (contrats §21, formats-incident.md, C2).

Ne vérifie que ce qui relève de la lecture (CAP-1) : les lignes illisibles et le nombre
d'événements lus. Les détections et indicateurs de l'oracle sont calibrés par C5.
"""

from pathlib import Path

import yaml

from waveaudit.adaptateurs.journaux import SourceJournauxFichiers

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


def test_oracle_ne_contient_aucune_valeur_reservee_au_faux_moteur():
    texte = (RACINE / "donnees" / "demo" / "incident-attendu.yaml").read_text(encoding="utf-8")
    for valeur in ("203.0.113.254", "0f" * 32, "T9999", "T1110.999"):
        assert valeur not in texte
