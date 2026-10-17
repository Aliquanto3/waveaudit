"""Mesure mémoire par psutil (port `MesureMemoire`, contrats §3 et §9, AD-11, CAP-12)."""

import psutil


class MesureMemoirePsutil:
    """Implémente `domaine.ports.MesureMemoire`."""

    def rss_octets(self, pid: int) -> int | None:
        """RSS du processus ; None s'il n'existe plus (ou n'est plus lisible)."""
        try:
            return psutil.Process(pid).memory_info().rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None


def ram_disponible_octets() -> int:
    """RAM disponible du poste, pour le choix du modèle de repli (AD-11)."""
    return psutil.virtual_memory().available
