"""Registre des workflows (contrats §5, AD-15)."""

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from waveaudit.domaine.configuration import Configuration
from waveaudit.domaine.modeles import Note, NoteInvalide, Rapport, ResultatElement
from waveaudit.domaine.ports import Ports


class Workflow(Protocol):
    def preparer(self, dossier: Path) -> list[Note | NoteInvalide]:
        """Lit les éléments via ports.source_notes."""
        ...

    def traiter(self, element: Note | NoteInvalide) -> ResultatElement:
        """Aucune entrée-sortie, aucun événement."""
        ...

    def assembler(self, resultats: list[ResultatElement]) -> Rapport: ...


def _creer_fiches(config: Configuration, ports: Ports) -> Workflow:
    # Import paresseux : `workflows.fiches.pipeline` arrive avec la story 10 ; le registre
    # n'a ainsi plus à être modifié.
    from waveaudit.workflows.fiches import pipeline

    return pipeline.creer(config, ports)


REGISTRE: dict[str, Callable[[Configuration, Ports], Workflow]] = {"fiches": _creer_fiches}
