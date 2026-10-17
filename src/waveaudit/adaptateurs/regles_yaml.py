"""Adaptateur du catalogue de règles de détection (CAP-2, contrats §21 « Règles »)."""

import ipaddress
import re
from pathlib import Path

import yaml
from pydantic import ValidationError

from waveaudit.domaine.erreurs import ConfigurationInvalide
from waveaudit.domaine.incident import (
    CHAMPS_LINUX,
    CHAMPS_WINDOWS,
    IDS_REGLES_MINIMAUX,
    MOTIF_HACHAGE,
    MOTIF_IPV4,
    MOTIF_IPV6,
    MOTIF_TECHNIQUE,
    PROGRAMMES_LINUX,
    Regle,
)

_URL_REFERENCE = re.compile(r"^https://attack\.mitre\.org/techniques/(T\d{4})(/(\d{3}))?/$")
# Rubriques textuelles d'une règle (distinctes de RUBRIQUES_RECIT : pas de "titre" requis
# ailleurs que dans les textes vérifiés ci-dessous, mais mêmes jetons interdits).
_RUBRIQUES_TEXTE_REGLE: tuple[str, ...] = ("description", "impact", "recommandation")
_LONGUEUR_MIN_TEXTE = 20


class CatalogueReglesYaml:
    """Charge le catalogue de règles depuis un dossier (implémente `CatalogueRegles`).

    Chaque `*.yaml` du dossier (trié) est une liste de règles. Toute erreur de validation
    ou de cohérence (`verifier_regles`) lève `ConfigurationInvalide` listant toutes les
    erreurs trouvées.
    """

    def __init__(self, dossier: Path) -> None:
        self._dossier = Path(dossier)
        regles: list[Regle] = []
        erreurs: list[str] = []

        for fichier in sorted(self._dossier.glob("*.yaml")):
            try:
                brut = yaml.safe_load(fichier.read_text(encoding="utf-8"))
            except (yaml.YAMLError, UnicodeDecodeError) as erreur:
                erreurs.append(f"{fichier.name}: YAML illisible ({_resumer(erreur)})")
                continue
            if brut is None:
                brut = []
            if not isinstance(brut, list):
                erreurs.append(f"{fichier.name}: la racine doit être une liste YAML")
                continue
            for index, entree in enumerate(brut):
                try:
                    regles.append(Regle.model_validate(entree))
                except ValidationError as erreur:
                    erreurs.append(f"{fichier.name}:{index}: règle invalide ({_resumer(erreur)})")

        erreurs.extend(verifier_regles(regles))
        if erreurs:
            raise ConfigurationInvalide("règles : " + "; ".join(erreurs))

        self._regles = sorted(regles, key=lambda r: r.id)

    def regles(self) -> list[Regle]:
        """Les règles du catalogue, triées par `id`."""
        return list(self._regles)


def verifier_regles(regles: list[Regle]) -> list[str]:
    """Contrôle la cohérence du catalogue (contrats §21 « Règles »). Liste des erreurs."""
    erreurs: list[str] = []

    _verifier_unicite(regles, erreurs)
    _verifier_minimum(regles, erreurs)

    for regle in regles:
        champs_autorises = CHAMPS_WINDOWS if regle.source == "windows" else CHAMPS_LINUX
        _verifier_cles(regle, champs_autorises, erreurs)
        _verifier_programme(regle, erreurs)
        _verifier_regex_compilables(regle, erreurs)
        _verifier_references(regle, erreurs)
        _verifier_textes(regle, erreurs)

    return erreurs


def _verifier_unicite(regles: list[Regle], erreurs: list[str]) -> None:
    vus: set[str] = set()
    doublons: set[str] = set()
    for regle in regles:
        if regle.id in vus:
            doublons.add(regle.id)
        vus.add(regle.id)
    for doublon in sorted(doublons):
        erreurs.append(f"{doublon}: identifiant dupliqué")


def _verifier_minimum(regles: list[Regle], erreurs: list[str]) -> None:
    presents = {regle.id for regle in regles}
    manquants = set(IDS_REGLES_MINIMAUX) - presents
    for manquant in sorted(manquants):
        erreurs.append(f"{manquant}: règle minimale manquante")


def _cles_condition(regle: Regle) -> set[str]:
    condition = regle.condition
    cles = set(condition.champs) | set(condition.champs_regex) | set(condition.au_moins_un)
    if regle.agregation is not None:
        cles |= set(regle.agregation.par)
    return cles


def _verifier_cles(regle: Regle, champs_autorises: frozenset[str], erreurs: list[str]) -> None:
    for cle in sorted(_cles_condition(regle) - champs_autorises):
        erreurs.append(f"{regle.id}: clé hors champs normalisés ({cle!r})")


def _verifier_programme(regle: Regle, erreurs: list[str]) -> None:
    programme = regle.condition.programme
    if programme is not None and programme not in PROGRAMMES_LINUX:
        erreurs.append(f"{regle.id}: programme non reconnu ({programme!r})")


def _regex_de_regle(regle: Regle) -> list[str]:
    condition = regle.condition
    motifs = list(condition.champs_regex.values()) + list(condition.au_moins_un.values())
    if condition.message_regex is not None:
        motifs.append(condition.message_regex)
    return motifs


def _verifier_regex_compilables(regle: Regle, erreurs: list[str]) -> None:
    for motif in _regex_de_regle(regle):
        try:
            re.compile(motif)
        except re.error as erreur:
            erreurs.append(f"{regle.id}: regex non compilable ({motif!r} : {erreur})")


def _verifier_references(regle: Regle, erreurs: list[str]) -> None:
    for reference in regle.references:
        trouve = _URL_REFERENCE.fullmatch(reference.url)
        if trouve is None:
            erreurs.append(f"{regle.id}: url de référence invalide ({reference.url!r})")
            continue
        base, _groupe, sous = trouve.group(1), trouve.group(2), trouve.group(3)
        id_attendu = f"{base}.{sous}" if sous else base
        if reference.id != id_attendu:
            erreurs.append(
                f"{regle.id}: url {reference.url!r} incohérente avec la référence {reference.id!r}"
            )


def _verifier_textes(regle: Regle, erreurs: list[str]) -> None:
    if not regle.titre.strip():
        erreurs.append(f"{regle.id}: titre vide")
    for rubrique in _RUBRIQUES_TEXTE_REGLE:
        texte = getattr(regle, rubrique)
        if len(texte) < _LONGUEUR_MIN_TEXTE:
            erreurs.append(
                f"{regle.id}: {rubrique} trop court (moins de {_LONGUEUR_MIN_TEXTE} caractères)"
            )
    for rubrique in ("titre", *_RUBRIQUES_TEXTE_REGLE):
        texte = getattr(regle, rubrique)
        if MOTIF_TECHNIQUE.search(texte):
            erreurs.append(f"{regle.id}: jeton ATT&CK interdit dans {rubrique}")
        if MOTIF_IPV4.search(texte):
            erreurs.append(f"{regle.id}: adresse IPv4 interdite dans {rubrique}")
        if _contient_ipv6(texte):
            erreurs.append(f"{regle.id}: adresse IPv6 interdite dans {rubrique}")
        if MOTIF_HACHAGE.search(texte):
            erreurs.append(f"{regle.id}: hachage interdit dans {rubrique}")


def _contient_ipv6(texte: str) -> bool:
    for candidat in MOTIF_IPV6.finditer(texte):
        try:
            ipaddress.ip_address(candidat.group())
        except ValueError:
            continue
        return True
    return False


def _resumer(erreur: Exception) -> str:
    if isinstance(erreur, ValidationError):
        return "; ".join(
            f"{'.'.join(str(x) for x in e['loc']) or 'racine'}: {e['msg']}" for e in erreur.errors()
        )
    return " ".join(str(erreur).split())
