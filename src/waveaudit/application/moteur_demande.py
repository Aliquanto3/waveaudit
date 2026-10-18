"""Verrou unique et moteur à la demande de l'UI (contrats §24, AD-11, AD-20).

`VerrouUnique` : un seul travail à la fois par processus UI (lot de fiches, incident,
régénération). `MoteurALaDemande` : le moteur de la régénération, ouvert par
`composition.ouvrir` (seul démarreur), réutilisé pour le même modèle résolu et fermé après
`ui.inactivite_moteur_s` sans usage. La CLI n'utilise ni l'un ni l'autre.
"""

import logging
import threading
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Literal

from waveaudit.application import composition
from waveaudit.domaine.configuration import Configuration
from waveaudit.domaine.ports import InfoMoteur, Ports
from waveaudit.installation import manifeste

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Occupation:
    nature: Literal["fiches", "incident", "regeneration"]
    id_lot: str
    index: int | None
    debut: datetime


class VerrouUnique:
    """Un par processus UI. Prise non bloquante ; état protégé par un verrou interne."""

    def __init__(self) -> None:
        self._verrou = threading.Lock()
        self._occupation: Occupation | None = None

    def prendre(self, occupation: Occupation) -> bool:
        """Non bloquant : False si un travail occupe déjà le verrou."""
        with self._verrou:
            if self._occupation is not None:
                return False
            self._occupation = occupation
            return True

    def definir(self, occupation: Occupation) -> None:
        """Remplace l'occupation provisoire (id du lot connu après la prise) [revue A1]."""
        with self._verrou:
            if self._occupation is None:
                raise RuntimeError("verrou non pris : definir sans prendre")
            self._occupation = occupation

    def liberer(self) -> None:
        with self._verrou:
            self._occupation = None

    def occupation(self) -> Occupation | None:
        """Copie de l'occupation courante, lue sous le verrou interne."""
        with self._verrou:
            return None if self._occupation is None else replace(self._occupation)


class MoteurALaDemande:
    """Un par processus UI ; sert seulement à la régénération, appelée sous `VerrouUnique`.

    [revue A10/E1] Verrou interne et compteur d'usages : l'entrée dans `utiliser` annule la
    minuterie sous ce verrou ; l'échéance ne ferme que si aucun usage n'est en cours et que la
    minuterie échue est encore la courante.
    """

    def __init__(self, config: Configuration) -> None:
        self._config = config
        self.inactivite_s = config.ui.inactivite_moteur_s
        self._verrou = threading.Lock()
        self._usages = 0
        self._minuterie: threading.Timer | None = None
        self._pile: ExitStack | None = None
        self._cle: str | None = None
        self._ouvert: tuple[Ports, InfoMoteur] | None = None
        self._nom_par_defaut: str | None = None

    def _cle_pour(self, modele: str | None) -> str:
        """[revue E10] Nom résolu ; le choix défaut/repli est figé au premier usage."""
        m = self._config.moteur
        if m.mode == "externe":
            return modele or m.modele_api
        if modele is None and self._nom_par_defaut is not None:
            return self._nom_par_defaut
        artefacts = manifeste.charger(self._config.chemins.manifeste)
        nom = composition.choisir_modele(self._config, artefacts, modele).nom
        if modele is None:
            self._nom_par_defaut = nom
        return nom

    def _fermer_moteur(self) -> None:
        """Sous `self._verrou`. L'état est remis à zéro avant l'arrêt du processus."""
        pile, self._pile, self._cle, self._ouvert = self._pile, None, None, None
        if pile is not None:
            pile.close()

    def _ouvrir_moteur(self, cle: str) -> tuple[Ports, InfoMoteur]:
        """Sous `self._verrou`. Un échec referme ce qui a été ouvert, puis remonte."""
        pile = ExitStack()
        try:
            ports, info = pile.enter_context(composition.ouvrir(self._config, cle or None))
            ports.moteur.sonder()
        except BaseException:
            pile.close()
            raise
        self._pile, self._cle, self._ouvert = pile, cle, (ports, info)
        return ports, info

    def _annuler_minuterie(self) -> None:
        """Sous `self._verrou`."""
        if self._minuterie is not None:
            self._minuterie.cancel()
            self._minuterie = None

    def _armer(self) -> None:
        """Sous `self._verrou` : annule la minuterie précédente et en arme une nouvelle."""
        self._annuler_minuterie()

        def echeance() -> None:
            self._echeance(minuterie)

        minuterie = threading.Timer(self.inactivite_s, echeance)
        minuterie.daemon = True
        self._minuterie = minuterie
        minuterie.start()

    def _echeance(self, minuterie: threading.Timer) -> None:
        with self._verrou:
            if minuterie is not self._minuterie or self._usages:
                return
            self._minuterie = None
            try:
                self._fermer_moteur()
            except Exception:  # noqa: BLE001 - fil de la minuterie : rien à qui remonter
                _log.warning("arrêt du moteur après inactivité en échec", exc_info=True)

    @contextmanager
    def utiliser(self, modele: str | None) -> Iterator[tuple[Ports, InfoMoteur]]:
        with self._verrou:
            self._usages += 1
            if self._minuterie is not None:
                self._minuterie.cancel()
                self._minuterie = None
        try:
            with self._verrou:
                cle = self._cle_pour(modele)
                if self._ouvert is not None and self._cle == cle:
                    ouvert = self._ouvert
                else:
                    self._fermer_moteur()
                    ouvert = self._ouvrir_moteur(cle)
            yield ouvert
        finally:
            with self._verrou:
                self._usages -= 1
                if self._usages == 0 and self._ouvert is not None:
                    self._armer()

    def fermer(self, timeout: float | None = None) -> None:
        """Idempotent : annule la minuterie et ferme le moteur s'il est ouvert.

        [v2, ARR] Sans `timeout` (défaut) : attend le verrou interne comme avant. Avec un
        `timeout`, ne l'attend pas au-delà : `utiliser()` peut le tenir jusqu'à
        `delai_demarrage_s` (contrats §24) pendant une ouverture de llama-server. Au-delà du
        délai, le llama-server déjà lancé est terminé directement via le filet de
        `composition` ; le fil qui ouvrait le détecte à son prochain sondage `/health` et
        libère le verrou de lui-même en levant `MoteurInjoignable`.
        """
        if timeout is None:
            with self._verrou:
                self._annuler_minuterie()
                self._fermer_moteur()
            return
        if self._verrou.acquire(timeout=timeout):
            try:
                self._annuler_minuterie()
                self._fermer_moteur()
            finally:
                self._verrou.release()
            return
        _log.warning(
            "fermeture du moteur : ouverture en cours au-delà du délai, arrêt forcé du llama-server"
        )
        composition.terminer_llama_server_en_cours()
