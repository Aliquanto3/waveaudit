"""Formes, constantes et schéma du workflow incident (contrats §21, AD-17).

Conditions des règles, champs normalisés et chronologie de démo : `formats-incident.md`
(normatif). Les constantes sont importées par les stories C2 à C5, jamais redéfinies.
"""

import re
from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from waveaudit.domaine.modeles import Motif, Reference, Statut

_CONFIG = ConfigDict(extra="forbid", frozen=True)

Severite = Literal["critique", "elevee", "moyenne", "faible"]
SourceJournal = Literal["windows", "linux"]

SEVERITES: tuple[str, ...] = ("critique", "elevee", "moyenne", "faible")
LIBELLES_SEVERITE: dict[str, str] = {
    "critique": "Critique",
    "elevee": "Élevée",
    "moyenne": "Moyenne",
    "faible": "Faible",
}
TYPES_INDICATEUR: tuple[str, ...] = ("compte", "executable", "hachage", "hote", "ip")

# Clés utilisables par une règle (tables « Champs normalisés » de formats-incident.md).
CHAMPS_WINDOWS: frozenset[str] = frozenset(
    {
        # 4624, 4625
        "TargetUserName",
        "TargetDomainName",
        "IpAddress",
        "IpPort",
        "LogonType",
        "WorkstationName",
        # 4720, 4728/4732/4756, 4698, 1102, 104, 4688
        "SubjectUserName",
        "MemberName",
        "TaskName",
        "Channel",
        # 7045
        "ServiceName",
        "ImagePath",
        "AccountName",
        # Sysmon 1, 4688
        "Image",
        "CommandLine",
        "ParentImage",
        "User",
        "Hashes",
        "NewProcessName",
        # Sysmon 10
        "SourceImage",
        "TargetImage",
        "GrantedAccess",
        "SourceUser",
    }
)
CHAMPS_LINUX: frozenset[str] = frozenset(
    {"utilisateur", "ip", "port", "commande", "fichier_cible", "nouvel_utilisateur"}
)
PROGRAMMES_LINUX: frozenset[str] = frozenset({"sshd", "sudo", "useradd"})

IDS_REGLES_MINIMAUX: tuple[str, ...] = (
    "INC-WIN-FORCE-BRUTE",
    "INC-WIN-CONNEXION-RDP",
    "INC-WIN-COMPTE-CREE",
    "INC-WIN-AJOUT-GROUPE-ADMIN",
    "INC-WIN-JOURNAL-EFFACE",
    "INC-WIN-SERVICE-INSTALLE",
    "INC-WIN-TACHE-PLANIFIEE",
    "INC-WIN-POWERSHELL-ENCODE",
    "INC-WIN-ACCES-LSASS",
    "INC-WIN-OUTIL-OFFENSIF",
    "INC-LIN-SSH-FORCE-BRUTE",
    "INC-LIN-SSH-CONNEXION-ROOT",
    "INC-LIN-SUDO-SHELL",
    "INC-LIN-COMPTE-CREE",
    "INC-LIN-CLE-SSH-AJOUTEE",
)

MOTIF_TECHNIQUE = re.compile(r"(?<![A-Za-z0-9])T\d{4}(?:\.\d{3})?(?![\d.])", re.IGNORECASE)
MOTIF_IPV4 = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
# Candidat seulement : à valider par `ipaddress.ip_address`.
MOTIF_IPV6 = re.compile(r"(?<![0-9A-Fa-f:])[0-9A-Fa-f:]*:[0-9A-Fa-f:]*:[0-9A-Fa-f:.]*")
MOTIF_HACHAGE = re.compile(
    r"(?<![0-9A-Fa-f])(?:[0-9A-Fa-f]{64}|[0-9A-Fa-f]{40}|[0-9A-Fa-f]{32})(?![0-9A-Fa-f])"
)

_ID_REGLE = re.compile(r"^INC-(WIN|LIN)-[A-Z0-9]+(-[A-Z0-9]+)*$")
_PREFIXE_SOURCE = {"WIN": "windows", "LIN": "linux"}
RUBRIQUES_RECIT: tuple[str, ...] = ("titre", "recit", "impact", "recommandation")


def _nom_seul(valeur: str) -> str:
    """Même règle que `Note.fichier` : un nom de fichier, jamais un chemin."""
    if not valeur or "/" in valeur or "\\" in valeur or valeur in {".", ".."}:
        raise ValueError("fichier doit être un nom de fichier seul, sans chemin")
    return valeur


class Evenement(BaseModel):
    """Événement normalisé. Non hachable (`champs` est un dict) : utiliser `cle`."""

    model_config = _CONFIG

    source: SourceJournal
    fichier: str
    ligne: int = Field(ge=1)
    horodatage: AwareDatetime
    hote: str
    event_id: int | None
    log_name: str | None
    programme: str | None
    message: str
    champs: dict[str, str]

    fichier_nom_seul = field_validator("fichier")(_nom_seul)

    @property
    def cle(self) -> tuple[str, int]:
        return (self.fichier, self.ligne)


class LigneIgnoree(BaseModel):
    model_config = _CONFIG

    fichier: str
    ligne: int = Field(ge=1)
    raison: str  # libre, non comparée

    fichier_nom_seul = field_validator("fichier")(_nom_seul)


class LectureJournaux(BaseModel):
    model_config = _CONFIG

    evenements: list[Evenement]
    ignorees: list[LigneIgnoree]
    fichiers: dict[str, int]  # nom -> enregistrements examinés (événements + ignorées)


class Condition(BaseModel):
    model_config = _CONFIG

    event_id: list[int] | None = None
    log_name: str | None = None
    programme: str | None = None
    champs: dict[str, str] = {}
    champs_regex: dict[str, str] = {}
    au_moins_un: dict[str, str] = {}
    message_regex: str | None = None

    @model_validator(mode="after")
    def _au_moins_un_critere(self) -> "Condition":
        if not any(getattr(self, nom) for nom in type(self).model_fields):
            raise ValueError("la condition doit avoir au moins un critère non vide")
        return self


class Agregation(BaseModel):
    model_config = _CONFIG

    seuil: int = Field(ge=2)
    fenetre_s: int = Field(ge=1)
    par: list[str] = []


class Regle(BaseModel):
    model_config = _CONFIG

    id: str
    titre: str
    description: str
    impact: str
    recommandation: str
    severite: Severite
    references: list[Reference] = Field(min_length=1)
    source: SourceJournal
    condition: Condition
    agregation: Agregation | None = None

    @model_validator(mode="after")
    def _id_coherent(self) -> "Regle":
        trouve = _ID_REGLE.fullmatch(self.id)
        if trouve is None:
            raise ValueError(f"id de règle invalide : {self.id!r}")
        if _PREFIXE_SOURCE[trouve.group(1)] != self.source:
            raise ValueError(f"préfixe de {self.id} incohérent avec la source {self.source}")
        return self


class Indicateur(BaseModel):
    model_config = _CONFIG

    type: Literal["ip", "compte", "hote", "hachage", "executable"]
    valeur: str
    origines: list[str] = Field(min_length=1)  # "fichier:ligne"


class Detection(BaseModel):
    model_config = _CONFIG

    regle_id: str
    debut: AwareDatetime
    fin: AwareDatetime
    hotes: list[str]
    # tous les déclencheurs, triés (horodatage, fichier casefold, ligne)
    evenements: list[Evenement] = Field(min_length=1)
    indicateurs: list[Indicateur] = []

    @model_validator(mode="after")
    def _periode(self) -> "Detection":
        if self.debut > self.fin:
            raise ValueError("debut doit précéder ou égaler fin")
        return self


class Recit(BaseModel):
    model_config = _CONFIG

    detection: Detection
    regle_titre: str
    titre: str
    recit: str
    impact: str
    recommandation: str
    severite: Severite
    references: list[Reference]
    statut: Literal[Statut.OK, Statut.A_REVOIR]
    motifs: list[Motif]  # a_revoir <=> motifs non vide

    @model_validator(mode="after")
    def _statut_coherent(self) -> "Recit":
        if (self.statut == Statut.A_REVOIR) != bool(self.motifs):
            raise ValueError("statut a_revoir si et seulement si motifs n'est pas vide")
        return self


class RapportIncident(BaseModel):
    model_config = _CONFIG

    debut: AwareDatetime | None
    fin: AwareDatetime | None
    recits: list[Recit]
    indicateurs: list[Indicateur]
    actifs: list[str]
    recommandations: list[str]
    sources: dict[str, int]
    ignorees: list[LigneIgnoree]


class RequeteIncident(BaseModel):
    model_config = _CONFIG

    dossier: Path
    annee: int
    modele: str | None = None
    id_lot: str | None = None
    copie_rapport: Path | None = None


class ResultatIncident(BaseModel):
    model_config = _CONFIG

    id_lot: str
    dossier_sortie: Path
    rapport: RapportIncident
    chemin_rapport: Path
    duree_s: float


def schema_recit(longueur_max: int) -> dict:
    """JSON Schema du récit : 4 rubriques texte requises, sans propriété additionnelle."""
    return {
        "type": "object",
        "properties": {
            rubrique: {"type": "string", "minLength": 1, "maxLength": longueur_max}
            for rubrique in RUBRIQUES_RECIT
        },
        "required": list(RUBRIQUES_RECIT),
        "additionalProperties": False,
    }
