"""Fabriques de formes du workflow incident pour les tests (contrats §21).

Chaque fabrique renvoie une forme valide par défaut ; les arguments nommés remplacent les
champs (`evenement(ligne=3)`, `regle(agregation=None)`).
"""

from datetime import datetime, timedelta, timezone

from waveaudit.domaine.incident import Detection, Evenement, Recit, Regle
from waveaudit.domaine.modeles import Reference, Statut

FUSEAU = timezone(timedelta(hours=2))
HORODATAGE = datetime(2026, 10, 14, 8, 2, 10, tzinfo=FUSEAU)


def evenement(**surcharges) -> Evenement:
    donnees: dict = {
        "source": "linux",
        "fichier": "auth.log",
        "ligne": 1,
        "horodatage": HORODATAGE,
        "hote": "BASTION01",
        "event_id": None,
        "log_name": None,
        "programme": "sshd",
        "message": "Failed password for invalid user admin from 203.0.113.45 port 41001 ssh2",
        "champs": {"utilisateur": "admin", "ip": "203.0.113.45", "port": "41001"},
    }
    return Evenement.model_validate(donnees | surcharges)


def regle(**surcharges) -> Regle:
    donnees: dict = {
        "id": "INC-LIN-SSH-FORCE-BRUTE",
        "titre": "Force brute SSH",
        "description": "Nombreux échecs d'authentification SSH depuis une même adresse.",
        "impact": "Un attaquant peut deviner un mot de passe et ouvrir une session.",
        "recommandation": "Bloquer l'adresse source et imposer l'authentification par clé.",
        "severite": "elevee",
        "references": [
            {
                "id": "T1110.001",
                "titre": "Brute Force: Password Guessing",
                "url": "https://attack.mitre.org/techniques/T1110/001/",
            }
        ],
        "source": "linux",
        "condition": {"programme": "sshd", "message_regex": "^Failed password for "},
        "agregation": {"seuil": 5, "fenetre_s": 300, "par": ["ip"]},
    }
    return Regle.model_validate(donnees | surcharges)


def detection(**surcharges) -> Detection:
    evenements = surcharges.pop("evenements", None) or [evenement()]
    donnees: dict = {
        "regle_id": "INC-LIN-SSH-FORCE-BRUTE",
        "debut": evenements[0].horodatage,
        "fin": evenements[-1].horodatage,
        "hotes": sorted({e.hote for e in evenements}, key=str.casefold),
        "evenements": evenements,
    }
    return Detection.model_validate(donnees | surcharges)


def recit(**surcharges) -> Recit:
    donnees: dict = {
        "detection": detection(),
        "regle_titre": "Force brute SSH",
        "titre": "Force brute SSH sur BASTION01",
        "recit": "Huit échecs d'authentification SSH depuis la même adresse en 70 secondes.",
        "impact": "Un attaquant peut deviner un mot de passe et ouvrir une session.",
        "recommandation": "Bloquer l'adresse source et imposer l'authentification par clé.",
        "severite": "elevee",
        "references": [
            Reference(
                id="T1110.001",
                titre="Brute Force: Password Guessing",
                url="https://attack.mitre.org/techniques/T1110/001/",
            )
        ],
        "statut": Statut.OK,
        "motifs": [],
    }
    return Recit.model_validate(donnees | surcharges)
