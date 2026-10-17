"""Modèles partagés du domaine (contrats §1). Formes figées par AD-16 : ne pas les modifier."""

from enum import StrEnum
from pathlib import Path
from typing import Literal, get_args

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

_CONFIG = ConfigDict(extra="forbid", frozen=True)


class Statut(StrEnum):
    OK = "ok"
    A_REVOIR = "a_revoir"
    NON_TRAITEE = "non_traitee"
    NON_RATTACHEE = "non_rattachee"


class Reference(BaseModel):
    model_config = _CONFIG

    id: str
    titre: str
    url: str


class ConstatType(BaseModel):
    model_config = _CONFIG

    id: str
    titre: str
    famille: Literal["web", "ad", "infra", "config", "crypto", "autre"]
    mots_cles: list[str]
    description: str
    impact: str
    recommandation: str
    # "CVSS:3.1/" + exactement les 8 métriques de base, ordre AV/AC/PR/UI/S/C/I/A
    cvss_vecteur: str
    references: list[Reference] = Field(min_length=1)
    source: str  # origine et licence


class Note(BaseModel):
    model_config = _CONFIG

    fichier: str  # nom de fichier seul, jamais un chemin
    titre: str | None
    actif: str | None
    severite_pressentie: Literal["critique", "elevee", "moyenne", "faible", "info"] | None
    # transporté jusqu'à la traçabilité ; jamais lu par la recherche ni le prompt
    constat_attendu: str | None
    corps: str  # non vide après strip

    @field_validator("fichier")
    @classmethod
    def _nom_seul(cls, valeur: str) -> str:
        if not valeur or "/" in valeur or "\\" in valeur or valeur in {".", ".."}:
            raise ValueError("fichier doit être un nom de fichier seul, sans chemin")
        return valeur

    @field_validator("corps")
    @classmethod
    def _corps_non_vide(cls, valeur: str) -> str:
        if not valeur.strip():
            raise ValueError("le corps de la note est vide")
        return valeur


class NoteInvalide(BaseModel):
    model_config = _CONFIG

    fichier: str
    raison: str


class MetriquesCvss(BaseModel):
    model_config = _CONFIG

    AV: Literal["N", "A", "L", "P"]
    AC: Literal["L", "H"]
    PR: Literal["N", "L", "H"]
    UI: Literal["N", "R"]
    S: Literal["U", "C"]
    C: Literal["N", "L", "H"]
    I: Literal["N", "L", "H"]  # noqa: E741 - nom de la métrique CVSS
    A: Literal["N", "L", "H"]


class Cvss(BaseModel):
    model_config = _CONFIG

    vecteur: str
    score: float
    severite: Literal["aucune", "faible", "moyenne", "elevee", "critique"]


class CodeMotif(StrEnum):
    REFERENCE_RETIREE = "reference_retiree"
    VECTEUR_INVALIDE = "vecteur_invalide"
    RUBRIQUE_COMPLETEE = "rubrique_completee"
    NOTE_TRONQUEE = "note_tronquee"
    REPLI_SORTIE_INVALIDE = "repli_sortie_invalide"
    REPLI_MOTEUR = "repli_moteur"
    NOTE_INVALIDE = "note_invalide"
    AUCUN_CONSTAT = "aucun_constat"


class Motif(BaseModel):
    model_config = _CONFIG

    code: CodeMotif
    detail: str


class Candidat(BaseModel):
    model_config = _CONFIG

    id: str
    score: float


class Tracabilite(BaseModel):
    model_config = _CONFIG

    note: str
    constat_id: str
    candidats: list[Candidat]
    constat_attendu: str | None


class Fiche(BaseModel):
    model_config = _CONFIG

    titre: str
    description: str
    impact: str
    recommandation: str
    cvss: Cvss
    references: list[Reference]
    statut: Literal[Statut.OK, Statut.A_REVOIR]
    motifs: list[Motif]  # a_revoir <=> motifs non vide
    tracabilite: Tracabilite

    @model_validator(mode="after")
    def _statut_coherent(self) -> "Fiche":
        if (self.statut == Statut.A_REVOIR) != bool(self.motifs):
            raise ValueError("statut a_revoir si et seulement si motifs n'est pas vide")
        return self


class EntreeEcartee(BaseModel):
    model_config = _CONFIG

    note: str
    statut: Literal[Statut.NON_TRAITEE, Statut.NON_RATTACHEE]
    motif: Motif
    candidats: list[Candidat]
    constat_attendu: str | None


ResultatElement = Fiche | EntreeEcartee


class Rapport(BaseModel):
    model_config = _CONFIG

    fiches: list[Fiche]
    ecartees: list[EntreeEcartee]


class TypeEvenement(StrEnum):
    LOT_DEMARRE = "lot_demarre"
    FICHE_DEMARREE = "fiche_demarree"
    FICHE_TERMINEE = "fiche_terminee"
    FICHE_NON_TRAITEE = "fiche_non_traitee"
    FICHE_NON_RATTACHEE = "fiche_non_rattachee"
    LOT_TERMINE = "lot_termine"
    LOT_ECHOUE = "lot_echoue"


class EvenementLot(BaseModel):
    model_config = _CONFIG

    type: TypeEvenement
    horodatage: AwareDatetime  # datetime avec fuseau, sérialisé en ISO 8601
    index: int | None  # 1..total pour les événements de fiche, None sinon
    total: int
    note: str | None  # nom de fichier
    statut: Statut | None
    duree_s: float | None
    details: dict[str, str | int | float | None] = Field(default_factory=dict)


class RequeteLot(BaseModel):
    model_config = _CONFIG

    dossier: Path
    workflow: str = "fiches"
    modele: str | None = None  # surcharge moteur.modele (local-gere) ou moteur.modele_api (externe)
    id_lot: str | None = None  # None : généré par le lot
    copie_rapport: Path | None = None  # -o : copie de rapport.docx en plus de var/sorties/<id>/


class ResultatLot(BaseModel):
    model_config = _CONFIG

    id_lot: str
    dossier_sortie: Path
    rapport: Rapport
    chemin_rapport: Path
    duree_s: float


RUBRIQUES: tuple[str, ...] = ("titre", "description", "impact", "recommandation")


def schema_sortie(longueur_max: int) -> dict:
    """JSON Schema de la sortie du moteur : 4 rubriques et métriques CVSS en enums.

    Sans `$ref` ni `$defs`, `additionalProperties: false` à chaque niveau, tous les champs
    requis, aucun champ de références.
    """
    metriques = {
        nom: {"type": "string", "enum": list(get_args(champ.annotation))}
        for nom, champ in MetriquesCvss.model_fields.items()
    }
    proprietes: dict[str, dict] = {
        rubrique: {"type": "string", "minLength": 1, "maxLength": longueur_max}
        for rubrique in RUBRIQUES
    }
    proprietes["cvss"] = {
        "type": "object",
        "properties": metriques,
        "required": list(metriques),
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": proprietes,
        "required": list(proprietes),
        "additionalProperties": False,
    }
