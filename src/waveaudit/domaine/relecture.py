"""État de relecture d'un lot de fiches : formes et invariants (contrats §25, story de socle v2).

Fichier `var/sorties/<id_lot>/relecture.json` = `EtatRelecture.model_dump_json(indent=2)`.
Les règles pures (`corriger`, `valider`, `remplacer_fiche`, `fiche_courante`, `rapport_export`)
sont ajoutées par la story R1 ; la persistance est dans `application/relecture.py` (R2).
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from waveaudit.domaine.erreurs import EntreeInvalide
from waveaudit.domaine.modeles import (
    Candidat,
    Cvss,
    EntreeEcartee,
    Fiche,
    Langue,
    Note,
    Reference,
)

_CONFIG = ConfigDict(extra="forbid", frozen=True)

StatutRelecture = Literal["a_valider", "validee"]
EtatEntree = Literal["attente", "fiche", "ecartee"]
EtatGeneration = Literal["aucune", "en_cours", "echec"]


class FicheCorrigee(BaseModel):
    """Version corrigée par le consultant d'une fiche générée."""

    model_config = _CONFIG

    titre: str
    description: str
    impact: str
    recommandation: str
    cvss_vecteur: str = Field(max_length=100)  # saisi tel quel, éventuellement invalide
    cvss: Cvss | None  # cvss31.evaluer(cvss_vecteur), None si invalide
    references: list[Reference]  # sous-ensemble ordonné de fiche_generee.references


class EntreeRelecture(BaseModel):
    """Une note du lot, dans l'ordre des événements (tri casefold du nom de fichier)."""

    model_config = _CONFIG

    index: int = Field(ge=1)  # rang dans le lot = index des événements
    note: str  # nom de fichier seul
    source: Note | None  # None pour une NoteInvalide (ou un lot v0.1.0 reconstruit)
    raison_invalide: str | None
    etat: EtatEntree
    candidats: list[Candidat]  # top 3 de la recherche (vide pour une note invalide)
    candidat_choisi: str | None  # constat de la fiche courante
    fiche_generee: Fiche | None
    fiche_corrigee: FicheCorrigee | None
    ecartee: EntreeEcartee | None
    statut_relecture: StatutRelecture | None
    generation: EtatGeneration = "aucune"
    erreur_generation: str | None = None
    # [revue A16] nom du modèle qui a produit fiche_generee (InfoMoteur.nom_modele)
    modele_generation: str | None = None
    version: int = Field(1, ge=1)  # +1 à chaque écriture de cette entrée

    @model_validator(mode="after")
    def _invariants(self) -> "EntreeRelecture":
        fiche = self.etat == "fiche"
        if fiche != (self.fiche_generee is not None) or fiche != (
            self.statut_relecture is not None
        ):
            raise ValueError(
                "etat 'fiche' si et seulement si fiche_generee et statut_relecture renseignés"
            )
        if (self.etat == "ecartee") != (self.ecartee is not None):
            raise ValueError("etat 'ecartee' si et seulement si ecartee renseignée")
        if self.fiche_corrigee is not None and not fiche:
            raise ValueError("fiche_corrigee exige etat 'fiche'")
        if self.candidat_choisi is not None and not self._candidat_admis(self.candidat_choisi):
            raise ValueError("candidat_choisi hors des candidats de la recherche")
        return self

    def _candidat_admis(self, constat_id: str) -> bool:
        if constat_id in {c.id for c in self.candidats}:
            return True
        # [revue A14] Entrée générée depuis `non_rattachee` (aucun candidat de score > 0) :
        # le constat est choisi dans tout le catalogue ; son existence est contrôlée par la route.
        return self.etat == "fiche" and all(c.score <= 0.0 for c in self.candidats)


class EtatRelecture(BaseModel):
    """Contenu de `relecture.json`."""

    model_config = _CONFIG

    version_schema: Literal[1] = 1
    id_lot: str
    langue: Langue
    modele: str  # nom affiché (InfoMoteur.nom_modele)
    modele_demande: str | None  # RequeteLot.modele tel que reçu
    entrees: list[EntreeRelecture]  # triées par index

    @model_validator(mode="after")
    def _entrees_triees(self) -> "EtatRelecture":
        index = [e.index for e in self.entrees]
        if any(a >= b for a, b in zip(index, index[1:], strict=False)):
            raise ValueError("entrees doivent être triées par index strictement croissant")
        return self


class RefusRelecture(EntreeInvalide):
    """Refus d'une opération de relecture ; `code` est repris tel quel par l'API (§26)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
