"""Adaptateur du catalogue de constats types (CAP-2, contrats §15, §16)."""

import re
from pathlib import Path

import yaml
from pydantic import ValidationError

from waveaudit.domaine.cvss31 import metriques_depuis_vecteur
from waveaudit.domaine.cvss31 import vecteur as vecteur_canonique
from waveaudit.domaine.erreurs import ConfigurationInvalide, EntreeInvalide
from waveaudit.domaine.modeles import ConstatType

# Identifiants figés par contrats §16 (au moins ces 35, d'autres peuvent s'ajouter).
IDENTIFIANTS_FIGES: frozenset[str] = frozenset(
    {
        "WEB-XSS-REFLECHI",
        "WEB-XSS-STOCKE",
        "WEB-INJECTION-SQL",
        "WEB-CSRF",
        "WEB-IDOR",
        "WEB-SSRF",
        "WEB-TRAVERSEE-CHEMIN",
        "WEB-UPLOAD-NON-RESTREINT",
        "WEB-SESSION-FIXATION",
        "WEB-ENTETES-SECURITE",
        "WEB-CORS-PERMISSIF",
        "WEB-REDIRECTION-OUVERTE",
        "WEB-DIVULGATION-ERREURS",
        "WEB-AUTH-FORCE-BRUTE",
        "WEB-XXE",
        "WEB-DESERIALISATION",
        "AD-KERBEROASTING",
        "AD-ASREP-ROASTING",
        "AD-DELEGATION-NON-CONTRAINTE",
        "AD-LAPS-ABSENT",
        "AD-ADMINS-EXCESSIFS",
        "AD-GPP-MOT-DE-PASSE",
        "INFRA-SMB-SIGNATURE",
        "INFRA-SERVICE-OBSOLETE",
        "INFRA-SNMP-COMMUNAUTE",
        "INFRA-RDP-EXPOSE",
        "INFRA-LLMNR-NBTNS",
        "CONFIG-MOT-DE-PASSE-DEFAUT",
        "CONFIG-SECRETS-EN-CLAIR",
        "CONFIG-LISTAGE-REPERTOIRE",
        "CONFIG-DEBUG-ACTIF",
        "CRYPTO-TLS-OBSOLETE",
        "CRYPTO-CERTIFICAT-INVALIDE",
        "CRYPTO-HACHAGE-FAIBLE",
        "AUTRE-JOURNALISATION-INSUFFISANTE",
    }
)

TOTAL_MINIMAL = 30

# Formes canoniques de référence acceptées (contrats §15) : CWE-79, CAPEC-63, WSTG-INPV-01,
# A03:2021, ANSSI-<SIGLE>, CERTFR-AAAA-XXX-NNN.
_RE_REFERENCE = re.compile(
    r"^(CWE-\d+|CAPEC-\d+|WSTG-[A-Z]+-\d+|A\d{2}:\d{4}|ANSSI-[A-Z0-9-]+|CERTFR-\d{4}-[A-Z]+-\d+)$"
)


class CatalogueYaml:
    """Lit le catalogue de constats types depuis `donnees/catalogue/<famille>.yaml`.

    Implémente le port `domaine.ports.Catalogue` (contrats §15).
    """

    def __init__(self, dossier: Path) -> None:
        self._dossier = Path(dossier)

    def constats(self) -> list[ConstatType]:
        """Tous les constats, triés par `id`. `ConfigurationInvalide` si invalides ou dupliqués."""
        constats: list[ConstatType] = []
        for fichier in sorted(self._dossier.glob("*.yaml")):
            for index, entree in _lire_fichier(fichier):
                try:
                    constats.append(ConstatType.model_validate(entree))
                except ValidationError as erreur:
                    raise ConfigurationInvalide(
                        f"{fichier.name}:{index}: constat type invalide ({erreur})"
                    ) from erreur
        constats.sort(key=lambda constat: constat.id)
        ids = [constat.id for constat in constats]
        if len(ids) != len(set(ids)):
            doublons = sorted({i for i in ids if ids.count(i) > 1})
            raise ConfigurationInvalide(
                f"catalogue : identifiants dupliqués ({', '.join(doublons)})"
            )
        return constats

    def obtenir(self, id: str) -> ConstatType:
        """Le constat type d'identifiant `id`. Lève `EntreeInvalide` si absent."""
        for constat in self.constats():
            if constat.id == id:
                return constat
        raise EntreeInvalide(f"constat type inconnu : {id!r}")


def _lire_fichier(fichier: Path) -> list[tuple[int, object]]:
    try:
        brut = yaml.safe_load(fichier.read_text(encoding="utf-8"))
    except (yaml.YAMLError, UnicodeDecodeError) as erreur:
        raise ConfigurationInvalide(f"{fichier.name}: YAML illisible ({erreur})") from erreur
    if brut is None:
        brut = []
    if not isinstance(brut, list):
        raise ConfigurationInvalide(f"{fichier.name}: la racine doit être une liste YAML")
    return list(enumerate(brut))


def verifier(dossier: Path) -> list[str]:
    """Contrôle le catalogue du dossier donné (contrats §15). Renvoie la liste des erreurs.

    Une liste vide signifie un catalogue valide. Chaque erreur est de la forme
    `fichier:id: message` (ou `fichier:index: message` si l'identifiant est inconnu).
    """
    dossier = Path(dossier)
    erreurs: list[str] = []
    identifiants: list[str] = []

    for fichier in sorted(dossier.glob("*.yaml")):
        try:
            entrees = _lire_fichier(fichier)
        except ConfigurationInvalide as erreur:
            erreurs.append(str(erreur))
            continue

        famille_attendue = fichier.stem
        prefixe_attendu = f"{famille_attendue.upper()}-"

        for index, entree in entrees:
            cle = entree.get("id", index) if isinstance(entree, dict) else index
            try:
                constat = ConstatType.model_validate(entree)
            except ValidationError as erreur:
                erreurs.append(f"{fichier.name}:{cle}: constat type invalide ({erreur})")
                continue

            identifiants.append(constat.id)

            if constat.famille != famille_attendue or not constat.id.startswith(prefixe_attendu):
                erreurs.append(
                    f"{fichier.name}:{constat.id}: la famille et le préfixe de l'id doivent "
                    f"correspondre au fichier ({prefixe_attendu!r})"
                )

            _verifier_vecteur(fichier, constat, erreurs)
            _verifier_references(fichier, constat, erreurs)

    _verifier_unicite(identifiants, erreurs)
    _verifier_identifiants_figes(identifiants, erreurs)

    if len(identifiants) < TOTAL_MINIMAL:
        erreurs.append(
            f"catalogue: {len(identifiants)} constat(s), au moins {TOTAL_MINIMAL} attendus"
        )

    return erreurs


def _verifier_vecteur(fichier: Path, constat: ConstatType, erreurs: list[str]) -> None:
    try:
        metriques = metriques_depuis_vecteur(constat.cvss_vecteur)
    except EntreeInvalide as erreur:
        erreurs.append(f"{fichier.name}:{constat.id}: {erreur}")
        return
    if vecteur_canonique(metriques) != constat.cvss_vecteur:
        erreurs.append(
            f"{fichier.name}:{constat.id}: cvss_vecteur non canonique "
            f"(attendu {vecteur_canonique(metriques)!r})"
        )


def _verifier_references(fichier: Path, constat: ConstatType, erreurs: list[str]) -> None:
    if not constat.references:
        erreurs.append(f"{fichier.name}:{constat.id}: au moins une référence requise")
        return
    for reference in constat.references:
        if not _RE_REFERENCE.match(reference.id):
            erreurs.append(
                f"{fichier.name}:{constat.id}: référence {reference.id!r} de forme non canonique"
            )
        if not reference.url.startswith("https://"):
            erreurs.append(
                f"{fichier.name}:{constat.id}: url de référence non https ({reference.url!r})"
            )


def _verifier_unicite(identifiants: list[str], erreurs: list[str]) -> None:
    vus: set[str] = set()
    doublons: set[str] = set()
    for identifiant in identifiants:
        if identifiant in vus:
            doublons.add(identifiant)
        vus.add(identifiant)
    for doublon in sorted(doublons):
        erreurs.append(f"catalogue:{doublon}: identifiant dupliqué")


def _verifier_identifiants_figes(identifiants: list[str], erreurs: list[str]) -> None:
    manquants = IDENTIFIANTS_FIGES - set(identifiants)
    for manquant in sorted(manquants):
        erreurs.append(f"catalogue:{manquant}: identifiant figé manquant (contrats §16)")
