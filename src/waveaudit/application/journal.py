"""Écrivain unique de `journal.jsonl` (contrats §21 « Composition et journal », AD-8).

Utilisé par le lot des fiches (`lot.py`) et par le workflow incident : un `EvenementLot` par
ligne (`model_dump_json()`), en ajout, vidé sur disque après chaque événement.
"""

from pathlib import Path
from types import TracebackType
from typing import Self

from waveaudit.domaine.modeles import EvenementLot


class JournalLot:
    """Ouvre `chemin` en ajout (UTF-8) ; à utiliser comme gestionnaire de contexte."""

    def __init__(self, chemin: Path) -> None:
        self._fichier = Path(chemin).open("a", encoding="utf-8")

    def ecrire(self, evenement: EvenementLot) -> None:
        self._fichier.write(evenement.model_dump_json() + "\n")
        self._fichier.flush()

    def fermer(self) -> None:
        self._fichier.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.fermer()
