"""Ports du domaine (contrats §3). Les adaptateurs les implémentent ; formes figées par AD-16."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol, TypedDict

from waveaudit.domaine.incident import LectureJournaux, RapportIncident, Regle
from waveaudit.domaine.modeles import ConstatType, Note, NoteInvalide, Rapport


class Message(TypedDict):
    role: Literal["system", "user"]
    content: str


class Moteur(Protocol):
    def sonder(self) -> None:
        """GET {base_url}/models ; statut différent de 200 -> MoteurInjoignable."""
        ...

    def generer_json(self, messages: list[Message], schema: dict, *, max_tokens: int) -> dict: ...


class Catalogue(Protocol):
    def constats(self) -> list[ConstatType]:
        """Constats triés par id, ids uniques."""
        ...

    def obtenir(self, id: str) -> ConstatType:
        """EntreeInvalide si absent."""
        ...


class SourceNotes(Protocol):
    def lire(self, dossier: Path) -> list[Note | NoteInvalide]: ...


class Exporteur(Protocol):
    def exporter(self, rapport: Rapport, chemin: Path) -> None: ...


class MesureMemoire(Protocol):
    def rss_octets(self, pid: int) -> int | None:
        """None si le processus n'existe plus."""
        ...


@dataclass(frozen=True)
class Ports:
    moteur: Moteur
    catalogue: Catalogue
    source_notes: SourceNotes
    exporteur: Exporteur
    prefixe_systeme: str


@dataclass(frozen=True)
class InfoMoteur:
    nom_modele: str
    pid: int | None
    base_url: str


# Workflow incident (contrats §21, AD-17). Aucun processus ni connexion dans ces ports :
# le moteur est ouvert à part (`composition.ouvrir_moteur_incident`), s'il y a une détection.


class SourceJournaux(Protocol):
    def lire(self, dossier: Path, *, annee: int) -> LectureJournaux:
        """EntreeInvalide si le dossier est absent ou ne contient aucun fichier routé."""
        ...


class CatalogueRegles(Protocol):
    def regles(self) -> list[Regle]:
        """Règles triées par id."""
        ...


class ExporteurIncident(Protocol):
    def exporter(self, rapport: RapportIncident, chemin: Path) -> None: ...


@dataclass(frozen=True)
class PortsIncident:
    source_journaux: SourceJournaux
    regles: CatalogueRegles
    exporteur: ExporteurIncident
