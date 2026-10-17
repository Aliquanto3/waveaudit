"""Adaptateur de lecture des journaux CERT (CAP-1, contrats §21 « Lecture »)."""

from pathlib import Path

from waveaudit.adaptateurs import journaux_linux, journaux_windows
from waveaudit.domaine.erreurs import EntreeInvalide
from waveaudit.domaine.incident import Evenement, LectureJournaux, LigneIgnoree

_IGNORES = (".gz", ".zip", ".bz2", ".xz", ".yaml", ".yml", ".md", ".gitkeep")


def _router(nom: str) -> str | None:
    casefold = nom.casefold()
    if casefold.endswith(_IGNORES):
        return None
    if casefold.endswith(".json"):
        return "json"
    if casefold.endswith(".csv"):
        return "csv"
    if casefold.startswith(("auth.log", "syslog", "secure")) or casefold.endswith(".log"):
        return "linux"
    return None


def _decoder(donnees: bytes, *, repli_syslog: bool) -> str:
    if donnees[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return donnees.decode("utf-16")
    if repli_syslog:
        return donnees.decode("utf-8", errors="replace")
    return donnees.decode("utf-8-sig")


class SourceJournauxFichiers:
    """Lit les journaux Windows et Linux d'un dossier (contrats §21 « Lecture »).

    Implémente `domaine.ports.SourceJournaux`.
    """

    def __init__(self, decalage_syslog: str = "+02:00") -> None:
        self._decalage_syslog = decalage_syslog

    def lire(self, dossier: Path, *, annee: int) -> LectureJournaux:
        dossier = Path(dossier)
        if not dossier.is_dir():
            raise EntreeInvalide(f"journaux : dossier introuvable ({dossier})")
        fichiers = sorted(
            (
                chemin
                for chemin in dossier.iterdir()
                if chemin.is_file() and not chemin.name.startswith(".")
            ),
            key=lambda chemin: chemin.name.casefold(),
        )
        evenements: list[Evenement] = []
        ignorees: list[LigneIgnoree] = []
        examines: dict[str, int] = {}
        nb_routes = 0
        for chemin in fichiers:
            nature = _router(chemin.name)
            if nature is None:
                continue
            nb_routes += 1
            evs, ign = self._lire_fichier(chemin, nature, annee)
            evenements.extend(evs)
            ignorees.extend(ign)
            examines[chemin.name] = len(evs) + len(ign)
        if nb_routes == 0:
            raise EntreeInvalide(f"journaux : aucun fichier routé dans {dossier}")
        evenements.sort(key=lambda e: (e.horodatage, e.fichier.casefold(), e.ligne))
        return LectureJournaux(evenements=evenements, ignorees=ignorees, fichiers=examines)

    def _lire_fichier(
        self, chemin: Path, nature: str, annee: int
    ) -> tuple[list[Evenement], list[LigneIgnoree]]:
        donnees = chemin.read_bytes()
        if nature == "linux":
            texte = _decoder(donnees, repli_syslog=True)
            return journaux_linux.lire(
                texte, chemin.name, annee=annee, decalage=self._decalage_syslog
            )
        texte = _decoder(donnees, repli_syslog=False)
        if nature == "json":
            return journaux_windows.lire_json(texte, chemin.name)
        return journaux_windows.lire_csv(texte, chemin.name)
