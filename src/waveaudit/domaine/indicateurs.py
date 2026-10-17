"""Extraction déterministe des indicateurs de compromission (contrats §21, CAP-4).

Sources, normalisation, exclusions et tri : `formats-incident.md` (normatif). N'importe
jamais `domaine.detection`.
"""

import ipaddress
import re

from waveaudit.domaine.incident import MOTIF_IPV4, Evenement, Indicateur

_EVENT_IDS_GROUPE = {4728, 4732, 4756}
_COMPTES_EXCLUS_CF = {"", "-", "system", "local service", "network service", "anonymous logon"}
_ALGOS_VALIDES = {"MD5": 32, "SHA1": 40, "SHA256": 64}
_MOTIF_HACHAGE_CHAMP = re.compile(r"(?P<algo>[A-Za-z0-9]+)=(?P<valeur>[0-9A-Fa-f]+)")


def _normaliser_ip(candidat: str) -> str | None:
    """`ipaddress`, IPv4 mappée -> IPv4 ; exclut invalides, 0.0.0.0, 127.0.0.0/8, ::1, ::."""
    try:
        ip = ipaddress.ip_address(candidat)
    except ValueError:
        return None
    if isinstance(ip, ipaddress.IPv6Address):
        mappee = ip.ipv4_mapped
        if mappee is not None:
            ip = mappee
    if isinstance(ip, ipaddress.IPv4Address):
        if ip == ipaddress.IPv4Address("0.0.0.0") or ip in ipaddress.ip_network("127.0.0.0/8"):
            return None
    elif ip in (ipaddress.IPv6Address("::1"), ipaddress.IPv6Address("::")):
        return None
    return str(ip)


def extraire(evenements: list[Evenement]) -> list[Indicateur]:
    """Indicateurs distincts (type, valeur), triés, origines comprises (contrats §21)."""
    evenements_tries = sorted(
        evenements, key=lambda e: (e.horodatage, e.fichier.casefold(), e.ligne)
    )

    origines: dict[tuple[str, str], set[str]] = {}
    graphie_compte: dict[str, str] = {}

    def _ajouter(type_: str, valeur: str, evenement: Evenement) -> None:
        origines.setdefault((type_, valeur), set()).add(f"{evenement.fichier}:{evenement.ligne}")

    for evenement in evenements_tries:
        champs = evenement.champs

        for cle in ("IpAddress", "ip"):
            brut = champs.get(cle)
            if brut:
                normalisee = _normaliser_ip(brut)
                if normalisee is not None:
                    _ajouter("ip", normalisee, evenement)
        for correspondance in MOTIF_IPV4.finditer(evenement.message):
            normalisee = _normaliser_ip(correspondance.group(0))
            if normalisee is not None:
                _ajouter("ip", normalisee, evenement)

        cles_compte = ["SubjectUserName", "utilisateur", "nouvel_utilisateur"]
        if evenement.event_id not in _EVENT_IDS_GROUPE:
            cles_compte.insert(0, "TargetUserName")
        for cle in cles_compte:
            brut = champs.get(cle)
            if brut is None:
                continue
            valeur = brut.strip()
            cle_cf = valeur.casefold()
            if not valeur or cle_cf in _COMPTES_EXCLUS_CF or valeur.endswith("$"):
                continue
            graphie = graphie_compte.setdefault(cle_cf, valeur)
            _ajouter("compte", graphie, evenement)

        for cle in ("Image", "SourceImage", "ImagePath"):
            brut = champs.get(cle)
            if brut:
                _ajouter("executable", brut.lower(), evenement)

        brut_hachage = champs.get("Hashes")
        if brut_hachage:
            for morceau in brut_hachage.split(","):
                correspondance = _MOTIF_HACHAGE_CHAMP.fullmatch(morceau.strip())
                if correspondance is None:
                    continue
                algo = correspondance.group("algo").upper()
                valeur = correspondance.group("valeur")
                longueur_attendue = _ALGOS_VALIDES.get(algo)
                if longueur_attendue is None or len(valeur) != longueur_attendue:
                    continue
                _ajouter("hachage", valeur.lower(), evenement)

        _ajouter("hote", evenement.hote.lower(), evenement)

    def _tri_origine(origine: str) -> tuple[str, int]:
        fichier, ligne = origine.rsplit(":", 1)
        return (fichier.casefold(), int(ligne))

    resultat = [
        Indicateur(type=type_, valeur=valeur, origines=sorted(origs, key=_tri_origine))
        for (type_, valeur), origs in origines.items()
    ]
    resultat.sort(key=lambda i: (i.type, i.valeur))
    return resultat
