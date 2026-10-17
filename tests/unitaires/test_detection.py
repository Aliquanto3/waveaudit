"""Moteur de détection déterministe (CAP-2, CAP-3, contrats §21 « Détection », C3)."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from tests.incident_outils import evenement, regle
from waveaudit.adaptateurs.regles_yaml import CatalogueReglesYaml
from waveaudit.domaine.detection import correspond, detecter
from waveaudit.domaine.incident import Evenement

DOSSIER_REGLES = Path(__file__).parents[2] / "donnees" / "regles"
FIXTURE = Path(__file__).parents[1] / "donnees" / "incident" / "canoniques.yaml"
ENTREES = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
REGLES = CatalogueReglesYaml(DOSSIER_REGLES).regles()

FUSEAU = timezone(timedelta(hours=2))


def _construire(entree: dict) -> Evenement:
    return Evenement.model_validate(
        entree["evenement"] | {"fichier": entree["fichier"], "ligne": entree["ligne"]}
    )


@pytest.mark.parametrize("entree", ENTREES, ids=[e["id"] for e in ENTREES])
def test_correspond_retrouve_exactement_les_regles_attendues(entree):
    ev = _construire(entree)
    trouvees = {r.id for r in REGLES if correspond(r, ev)}
    assert trouvees == set(entree["regles"]), entree["id"]


# --- Agrégation : vecteurs normatifs (contrats §21) -----------------------------------------


def _horodatage(secondes: float) -> datetime:
    return datetime(2026, 10, 14, 8, 0, 0, tzinfo=FUSEAU) + timedelta(seconds=secondes)


def _evenements_force_brute(instants: list[float], ip: str = "203.0.113.45") -> list[Evenement]:
    return [
        evenement(
            ligne=i + 1,
            horodatage=_horodatage(t),
            message=f"Failed password for invalid user admin from {ip} port {41000 + i} ssh2",
            champs={"utilisateur": "admin", "ip": ip, "port": str(41000 + i)},
        )
        for i, t in enumerate(instants)
    ]


def _bornes(detections) -> list[tuple[float, float]]:
    def _secondes(instant: datetime) -> float:
        return (instant - _horodatage(0)).total_seconds()

    return [(_secondes(d.debut), _secondes(d.fin)) for d in detections]


def test_agregation_seuil_3_fenetre_60_deux_groupes():
    r = regle(agregation={"seuil": 3, "fenetre_s": 60, "par": ["ip"]})
    evenements = _evenements_force_brute([0, 10, 20, 100, 110, 120])
    detections = detecter([r], evenements)
    assert _bornes(detections) == [(0, 20), (100, 120)]


def test_agregation_seuil_3_fenetre_60_perd_les_deux_premiers():
    r = regle(agregation={"seuil": 3, "fenetre_s": 60, "par": ["ip"]})
    evenements = _evenements_force_brute([0, 10, 70, 80, 90])
    detections = detecter([r], evenements)
    assert _bornes(detections) == [(70, 90)]
    assert len(detections[0].evenements) == 3


def test_agregation_seuil_3_fenetre_60_borne_incluse():
    r = regle(agregation={"seuil": 3, "fenetre_s": 60, "par": ["ip"]})
    evenements = _evenements_force_brute([0, 30, 60])
    detections = detecter([r], evenements)
    assert _bornes(detections) == [(0, 60)]


def test_agregation_seuil_3_fenetre_60_aucune_detection():
    r = regle(agregation={"seuil": 3, "fenetre_s": 60, "par": ["ip"]})
    evenements = _evenements_force_brute([0, 30, 61])
    detections = detecter([r], evenements)
    assert detections == []


def test_agregation_seuil_5_fenetre_300_une_detection_de_8():
    r = regle(agregation={"seuil": 5, "fenetre_s": 300, "par": ["ip"]})
    evenements = _evenements_force_brute([i * 60 for i in range(8)])
    detections = detecter([r], evenements)
    assert len(detections) == 1
    assert len(detections[0].evenements) == 8
    assert _bornes(detections) == [(0, 420)]


def test_agregation_seuil_copies_espacees_de_10s_donne_une_detection():
    r = regle(agregation={"seuil": 5, "fenetre_s": 300, "par": ["ip"]})
    evenements = _evenements_force_brute([0, 10, 20, 30, 40])
    detections = detecter([r], evenements)
    assert len(detections) == 1
    assert len(detections[0].evenements) == 5


def test_une_seule_copie_ne_donne_aucune_detection():
    r = regle(agregation={"seuil": 5, "fenetre_s": 300, "par": ["ip"]})
    evenements = _evenements_force_brute([0])
    assert detecter([r], evenements) == []


def test_evenement_sans_champ_par_non_compte():
    r = regle(agregation={"seuil": 2, "fenetre_s": 60, "par": ["ip"]})
    avec_ip = evenement(ligne=1, horodatage=_horodatage(0))
    sans_ip = evenement(ligne=2, horodatage=_horodatage(5), champs={"utilisateur": "admin"})
    detections = detecter([r], [avec_ip, sans_ip])
    assert detections == []


def test_sans_agregation_une_detection_par_evenement():
    r = regle(agregation=None)
    evenements = _evenements_force_brute([0, 300, 600])
    detections = detecter([r], evenements)
    assert len(detections) == 3
    assert all(len(d.evenements) == 1 for d in detections)
    assert all(d.debut == d.fin for d in detections)


# --- au_moins_un, clé absente ----------------------------------------------------------------


def test_au_moins_un_declenche_sur_une_seule_cle():
    r = [r for r in REGLES if r.id == "INC-WIN-OUTIL-OFFENSIF"][0]
    ev = evenement(
        source="windows",
        fichier="sysmon.csv",
        programme=None,
        event_id=1,
        log_name="Microsoft-Windows-Sysmon/Operational",
        message="Process Create",
        champs={"Image": r"C:\ProgramData\maj\mimikatz.exe"},
    )
    assert correspond(r, ev)


def test_au_moins_un_faux_si_aucune_cle_ne_correspond():
    r = [r for r in REGLES if r.id == "INC-WIN-OUTIL-OFFENSIF"][0]
    ev = evenement(
        source="windows",
        fichier="sysmon.csv",
        programme=None,
        event_id=1,
        log_name="Microsoft-Windows-Sysmon/Operational",
        message="Process Create",
        champs={"Image": r"C:\Windows\System32\notepad.exe"},
    )
    assert not correspond(r, ev)


def test_cle_absente_rend_le_critere_faux():
    r = regle(condition={"programme": "sudo", "champs_regex": {"commande": "authorized_keys"}})
    ev = evenement(
        programme="sudo", message="deploy : COMMAND=/bin/ls", champs={"utilisateur": "deploy"}
    )
    assert not correspond(r, ev)


# --- Déterminisme et tri final ----------------------------------------------------------------


def test_determinisme():
    regles = [r for r in REGLES if r.id in {"INC-LIN-SSH-FORCE-BRUTE", "INC-LIN-SUDO-SHELL"}]
    evenements = [
        evenement(ligne=1, horodatage=_horodatage(0)),
        evenement(
            ligne=2,
            horodatage=_horodatage(5),
            programme="sudo",
            message="deploy : COMMAND=/bin/bash",
            champs={"utilisateur": "deploy", "commande": "/bin/bash"},
        ),
    ]
    premiere = detecter(regles, evenements)
    seconde = detecter(regles, evenements)
    assert premiere == seconde


def test_tri_final_par_debut_puis_regle_id_puis_fichier_puis_ligne():
    r_sudo = regle(
        id="INC-LIN-SUDO-SHELL",
        condition={"programme": "sudo", "champs_regex": {"commande": "^/bin/bash"}},
        agregation=None,
    )
    r_force_brute = regle(agregation={"seuil": 2, "fenetre_s": 60, "par": ["ip"]})
    evenements = [
        evenement(
            ligne=2,
            fichier="auth.log",
            horodatage=_horodatage(0),
            programme="sudo",
            message="deploy : COMMAND=/bin/bash",
            champs={"utilisateur": "deploy", "commande": "/bin/bash"},
        ),
        *_evenements_force_brute([0, 5]),
    ]
    detections = detecter([r_sudo, r_force_brute], evenements)
    cles = [(d.debut, d.regle_id) for d in detections]
    assert cles == sorted(cles)
    # Même debut (t=0) : INC-LIN-SSH-FORCE-BRUTE < INC-LIN-SUDO-SHELL (ordre alphabétique).
    assert detections[0].regle_id == "INC-LIN-SSH-FORCE-BRUTE"
    assert detections[1].regle_id == "INC-LIN-SUDO-SHELL"


def test_detecter_laisse_les_indicateurs_vides():
    r = regle(agregation=None)
    detections = detecter([r], [evenement()])
    assert detections[0].indicateurs == []
