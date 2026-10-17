"""Lecture des journaux Linux (syslog RFC 3164 et rsyslog ISO) — contrats §21, CAP-1."""

import re
from datetime import date, datetime, time, timedelta, timezone

from waveaudit.domaine.incident import Evenement, LigneIgnoree

_MOIS = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}

_RFC3164 = re.compile(
    r"^(?P<mois>[A-Z][a-z]{2}) {1,2}(?P<jour>\d{1,2}) "
    r"(?P<heure>\d{2}:\d{2}:\d{2}) (?P<hote>\S+) "
    r"(?P<prog>[^\s:\[]+)(?:\[\d+\])?: ?(?P<message>.*)$"
)
_ISO = re.compile(
    r"^(?P<horodatage>\S+) (?P<hote>\S+) (?P<prog>[^\s:\[]+)(?:\[\d+\])?: ?(?P<message>.*)$"
)

_SSHD_ECHEC_OU_ACCEPTE = re.compile(
    r"^(?:Failed|Accepted) \S+ for (?:invalid user )?(?P<utilisateur>\S+) "
    r"from (?P<ip>\S+) port (?P<port>\d+)"
)
_SSHD_UTILISATEUR_INVALIDE = re.compile(
    r"^Invalid user (?P<utilisateur>\S+) from (?P<ip>\S+)(?: port (?P<port>\d+))?"
)
_SUDO_COMMANDE = re.compile(r"^(?P<utilisateur>\S+) : .*?\bCOMMAND=(?P<commande>.+)$")
_SUDO_FICHIER_CIBLE = re.compile(r"(?P<fichier_cible>/\S*authorized_keys2?)")
_USERADD_NOUVEL_UTILISATEUR = re.compile(r"new user: name=(?P<nouvel_utilisateur>[^,\s]+)")


def lire(
    texte: str, fichier: str, *, annee: int, decalage: str
) -> tuple[list[Evenement], list[LigneIgnoree]]:
    """Lit un contenu syslog déjà décodé (RFC 3164 ou rsyslog ISO 8601)."""
    fuseau = _fuseau(decalage)
    evenements: list[Evenement] = []
    ignorees: list[LigneIgnoree] = []
    annee_courante = annee
    dernier_mois: int | None = None
    for numero, brute in enumerate(texte.split("\n"), start=1):
        ligne_brute = brute[:-1] if brute.endswith("\r") else brute
        if not ligne_brute.strip():
            continue
        correspondance = _RFC3164.match(ligne_brute)
        if correspondance is not None and correspondance.group("mois") in _MOIS:
            mois = _MOIS[correspondance.group("mois")]
            if dernier_mois is not None and mois < dernier_mois:
                annee_courante += 1
            try:
                jour = int(correspondance.group("jour"))
                heure = time.fromisoformat(correspondance.group("heure"))
                horodatage = datetime.combine(
                    date(annee_courante, mois, jour), heure, tzinfo=fuseau
                )
            except ValueError:
                ignorees.append(
                    LigneIgnoree(fichier=fichier, ligne=numero, raison="date impossible")
                )
                continue
            dernier_mois = mois
            hote = correspondance.group("hote")
            programme = correspondance.group("prog")
            message = correspondance.group("message").strip()
        else:
            correspondance = _ISO.match(ligne_brute)
            horodatage = (
                _horodatage_iso(correspondance.group("horodatage"))
                if correspondance is not None
                else None
            )
            if correspondance is None or horodatage is None:
                ignorees.append(
                    LigneIgnoree(fichier=fichier, ligne=numero, raison="ligne non reconnue")
                )
                continue
            hote = correspondance.group("hote")
            programme = correspondance.group("prog")
            message = correspondance.group("message").strip()
        evenements.append(
            Evenement(
                source="linux",
                fichier=fichier,
                ligne=numero,
                horodatage=horodatage,
                hote=hote,
                event_id=None,
                log_name=None,
                programme=programme,
                message=message,
                champs=_champs(programme, message),
            )
        )
    return evenements, ignorees


def _fuseau(decalage: str) -> timezone:
    signe = -1 if decalage[0] == "-" else 1
    heures_str, minutes_str = decalage[1:].split(":")
    return timezone(signe * timedelta(hours=int(heures_str), minutes=int(minutes_str)))


def _horodatage_iso(valeur: str) -> datetime | None:
    try:
        horodatage = datetime.fromisoformat(valeur)
    except ValueError:
        return None
    return horodatage if horodatage.tzinfo is not None else None


def _champs(programme: str, message: str) -> dict[str, str]:
    if programme == "sshd":
        for motif in (_SSHD_ECHEC_OU_ACCEPTE, _SSHD_UTILISATEUR_INVALIDE):
            trouve = motif.search(message)
            if trouve:
                return {cle: valeur for cle, valeur in trouve.groupdict().items() if valeur}
        return {}
    if programme == "sudo":
        trouve = _SUDO_COMMANDE.search(message)
        if not trouve:
            return {}
        champs = {cle: valeur for cle, valeur in trouve.groupdict().items() if valeur}
        cible = _SUDO_FICHIER_CIBLE.search(champs.get("commande", ""))
        if cible:
            champs["fichier_cible"] = cible.group("fichier_cible")
        return champs
    if programme == "useradd":
        trouve = _USERADD_NOUVEL_UTILISATEUR.search(message)
        if trouve:
            return {cle: valeur for cle, valeur in trouve.groupdict().items() if valeur}
        return {}
    return {}
