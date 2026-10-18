"""Ports du domaine (contrats §3). Les adaptateurs les implémentent ; formes figées par AD-16."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol, TypedDict

from waveaudit.domaine.incident import LectureJournaux, RapportIncident, Regle
from waveaudit.domaine.modeles import ConstatType, Langue, Note, NoteInvalide, Rapport


class Message(TypedDict):
    role: Literal["system", "user"]
    content: str


class Moteur(Protocol):
    def sonder(self) -> None:
        """GET {base_url}/models ; statut différent de 200 -> MoteurInjoignable."""
        ...

    def generer_json(
        self, messages: list[Message], schema: dict, *, max_tokens: int, seed: int | None = None
    ) -> dict:
        """[v2] seed : None = seed configurée (contrats §3, §5)."""
        ...


class Catalogue(Protocol):
    def constats(self) -> list[ConstatType]:
        """Constats triés par id, ids uniques."""
        ...

    def obtenir(self, id: str) -> ConstatType:
        """EntreeInvalide si absent."""
        ...


class SourceNotes(Protocol):
    def lire(self, dossier: Path) -> list[Note | NoteInvalide]: ...


@dataclass(frozen=True)
class OptionsExport:
    """[v2] Options d'export Word (contrats §27)."""

    langue: Langue = "fr"
    mode: Literal["lot", "final", "brouillon"] = "lot"  # "lot" = rapport.docx v0.1.0, inchangé
    # Noms de note des fiches non validées : marquées « Non validée » en brouillon, listées en
    # annexe en final, jamais dans le corps du rapport final ([revue A17]).
    non_validees: frozenset[str] = frozenset()


class Exporteur(Protocol):
    def exporter(
        self,
        rapport: Rapport,
        chemin: Path,
        options: OptionsExport = OptionsExport(),  # noqa: B008 - dataclass figée, immuable
    ) -> None: ...


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
