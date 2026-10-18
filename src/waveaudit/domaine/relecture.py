"""État de relecture d'un lot de fiches : formes, invariants et règles pures (contrats §25).

Fichier `var/sorties/<id_lot>/relecture.json` = `EtatRelecture.model_dump_json(indent=2)`.
Les formes et invariants sont posées par la story de socle v2 (S0) ; les règles pures
(`fiche_courante`, `corriger`, `valider`, `remplacer_fiche`, `rapport_export`) sont ajoutées par
R1, en fonctions pures sans accès disque. La persistance est dans `application/relecture.py` (R2).
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from waveaudit.domaine import cvss31
from waveaudit.domaine.erreurs import EntreeInvalide
from waveaudit.domaine.modeles import (
    Candidat,
    CodeMotif,
    Cvss,
    EntreeEcartee,
    Fiche,
    Langue,
    Motif,
    Note,
    Rapport,
    Reference,
    Statut,
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


def fiche_courante(e: EntreeRelecture) -> Fiche:
    """Fiche à afficher : `fiche_generee` sans correction, ou corrigée (contrats §25)."""
    generee = e.fiche_generee
    corrigee = e.fiche_corrigee
    if corrigee is None:
        return generee
    # [revue E30] CVSS corrigé invalide (None) : la fiche courante (brouillon) garde le CVSS
    # généré ; une fiche validée a toujours un CVSS valide (vérifié par `valider`).
    cvss = corrigee.cvss if corrigee.cvss is not None else generee.cvss
    return generee.model_copy(
        update={
            "titre": corrigee.titre,
            "description": corrigee.description,
            "impact": corrigee.impact,
            "recommandation": corrigee.recommandation,
            "references": corrigee.references,
            "cvss": cvss,
        }
    )


def corriger(e: EntreeRelecture, correction: FicheCorrigee, longueur_max: int) -> EntreeRelecture:
    """Applique une correction du consultant à une entrée `fiche` (contrats §25)."""
    if e.etat != "fiche":
        raise RefusRelecture("non_modifiable", "Cette entrée n'a pas de fiche à corriger.")
    if e.generation == "en_cours":
        raise RefusRelecture("generation_en_cours", "Une régénération est en cours.")
    for rubrique in (
        correction.titre,
        correction.description,
        correction.impact,
        correction.recommandation,
    ):
        if len(rubrique) > longueur_max:
            raise RefusRelecture(
                "rubrique_trop_longue", f"Une rubrique dépasse {longueur_max} caractères."
            )
    ids_generee = [r.id for r in e.fiche_generee.references]
    ids_corrigee = [r.id for r in correction.references]
    if not set(ids_corrigee) <= set(ids_generee):
        raise RefusRelecture(
            "reference_ajoutee", "Une référence ajoutée n'est pas dans la fiche générée."
        )
    if len(set(ids_corrigee)) != len(ids_corrigee):
        # [revue E29]
        raise RefusRelecture("reference_dupliquee", "Une référence est répétée.")
    # Les références gardées sont rangées dans l'ordre de `fiche_generee.references`.
    references = [r for r in e.fiche_generee.references if r.id in ids_corrigee]
    try:
        cvss = cvss31.evaluer(correction.cvss_vecteur)
    except EntreeInvalide:
        # [revue E30] Vecteur invalide enregistré tel quel : la saisie n'est pas perdue.
        cvss = None
    nouvelle = FicheCorrigee(
        titre=correction.titre,
        description=correction.description,
        impact=correction.impact,
        recommandation=correction.recommandation,
        cvss_vecteur=correction.cvss_vecteur,
        cvss=cvss,
        references=references,
    )
    if nouvelle == (e.fiche_corrigee or _projection_generee(e.fiche_generee)):
        # Correction identique à l'état courant : rien ne change, ni la fiche ni le statut
        # (une fiche validée le reste). L'entrée reçue est renvoyée telle quelle ;
        # `application/relecture.modifier` (R2) n'incrémente pas la version d'une entrée égale.
        return e
    return _maj(e, fiche_corrigee=nouvelle, statut_relecture="a_valider")


def _projection_generee(fiche: Fiche) -> FicheCorrigee:
    """La fiche générée sous forme de correction, pour reconnaître une correction sans effet."""
    return FicheCorrigee(
        titre=fiche.titre,
        description=fiche.description,
        impact=fiche.impact,
        recommandation=fiche.recommandation,
        cvss_vecteur=fiche.cvss.vecteur,
        cvss=fiche.cvss,
        references=fiche.references,
    )


def _maj(e: EntreeRelecture, **champs: object) -> EntreeRelecture:
    """Copie revalidée : `model_copy` seul ne vérifie pas les invariants de `EntreeRelecture`."""
    return EntreeRelecture.model_validate(e.model_dump() | champs)


def valider(e: EntreeRelecture) -> EntreeRelecture:
    """Valide l'entrée `fiche` courante (contrats §25)."""
    if e.etat != "fiche":
        raise RefusRelecture("non_modifiable", "Cette entrée n'a pas de fiche à valider.")
    if e.generation == "en_cours":
        raise RefusRelecture("generation_en_cours", "Une régénération est en cours.")
    fiche = fiche_courante(e)
    if e.fiche_corrigee is not None and e.fiche_corrigee.cvss is None:
        raise RefusRelecture("vecteur_invalide", "Le vecteur CVSS corrigé n'est pas valide.")
    for rubrique in (fiche.titre, fiche.description, fiche.impact, fiche.recommandation):
        if not rubrique.strip():
            raise RefusRelecture("rubrique_vide", "Une rubrique de la fiche est vide.")
    return _maj(e, statut_relecture="validee")


def remplacer_fiche(
    e: EntreeRelecture, fiche: Fiche, constat_id: str, modele_generation: str
) -> EntreeRelecture:
    """Remplace la fiche courante par une fiche régénérée (contrats §25, §24)."""
    try:
        return _maj(
            e,
            etat="fiche",
            fiche_generee=fiche,
            fiche_corrigee=None,
            candidat_choisi=constat_id,
            ecartee=None,
            statut_relecture="a_valider",
            generation="aucune",
            erreur_generation=None,
            modele_generation=modele_generation,  # [revue A16]
        )
    except ValidationError as erreur:
        # Seul invariant atteignable : `candidat_choisi` hors des candidats (revue A14 : admis
        # seulement si aucun candidat n'a de score > 0, cas `non_rattachee`).
        raise RefusRelecture(
            "candidat_inconnu", "Ce constat n'est pas un candidat de cette note."
        ) from erreur


def rapport_export(
    etat: EtatRelecture, mode: Literal["final", "brouillon"]
) -> tuple[Rapport, frozenset[str]]:
    """Fiches et entrées écartées à exporter, plus les fiches encore `a_valider` (contrats §25)."""
    fiches_entrees = [e for e in etat.entrees if e.etat == "fiche"]
    if mode == "final":
        fiches = [fiche_courante(e) for e in fiches_entrees if e.statut_relecture == "validee"]
    else:
        fiches = [fiche_courante(e) for e in fiches_entrees]
    # [revue A17] final : l'ensemble renvoyé liste les fiches encore `a_valider` pour l'annexe ;
    # brouillon : même ensemble, mêmes notes `a_valider`.
    non_validees = frozenset(e.note for e in fiches_entrees if e.statut_relecture == "a_valider")
    ecartees_existantes = [(e.index, e.ecartee) for e in etat.entrees if e.etat == "ecartee"]
    # [revue E17] Les entrées `attente` d'un lot interrompu deviennent des entrées écartées.
    ecartees_interrompues = [
        (
            e.index,
            EntreeEcartee(
                note=e.note,
                statut=Statut.NON_TRAITEE,
                motif=Motif(
                    code=CodeMotif.LOT_INTERROMPU, detail="lot interrompu avant cette note"
                ),
                candidats=[],
                constat_attendu=e.source.constat_attendu if e.source else None,
            ),
        )
        for e in etat.entrees
        if e.etat == "attente"
    ]
    ecartees = [
        ecartee
        for _, ecartee in sorted(ecartees_existantes + ecartees_interrompues, key=lambda c: c[0])
    ]
    return Rapport(fiches=fiches, ecartees=ecartees), non_validees
