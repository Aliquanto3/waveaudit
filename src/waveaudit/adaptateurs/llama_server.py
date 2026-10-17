"""Cycle de vie de llama-server (contrats §10, AD-11). Démarré par `composition.ouvrir` seul.

Écoute sur 127.0.0.1 et un port libre, reçoit toujours `-c` et `-t`, est rattaché à un Job
Object `KILL_ON_JOB_CLOSE` sous Windows et écrit sa sortie dans un fichier, jamais dans un tube.
"""

import logging
import socket
import subprocess
import sys
import time
from pathlib import Path
from types import TracebackType
from typing import IO

import httpx

from waveaudit.domaine.erreurs import MoteurInjoignable

_log = logging.getLogger(__name__)

HOTE = "127.0.0.1"
PAS_ATTENTE_S = 0.1
DELAI_ARRET_S = 5.0


def port_libre() -> int:
    """Bind sur 127.0.0.1:0, lecture du port, fermeture."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((HOTE, 0))
        return sock.getsockname()[1]


class _JobWindows:
    """Job Object `KILL_ON_JOB_CLOSE` par ctypes ; le processus y entre via `OpenProcess`."""

    def __init__(self) -> None:
        import ctypes
        from ctypes import wintypes

        class _Basique(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_int64),
                ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class _Io(ctypes.Structure):
            _fields_ = [
                (nom, ctypes.c_uint64)
                for nom in ("Lectures", "Ecritures", "Autres", "OctetsLus", "OctetsEcrits", "Oct")
            ]

        class _Etendue(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", _Basique),
                ("IoInfo", _Io),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.CreateJobObjectW.argtypes = (wintypes.LPVOID, wintypes.LPCWSTR)
        k32.CreateJobObjectW.restype = wintypes.HANDLE
        k32.SetInformationJobObject.argtypes = (
            wintypes.HANDLE,
            ctypes.c_int,
            wintypes.LPVOID,
            wintypes.DWORD,
        )
        k32.SetInformationJobObject.restype = wintypes.BOOL
        k32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        k32.OpenProcess.restype = wintypes.HANDLE
        k32.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
        k32.AssignProcessToJobObject.restype = wintypes.BOOL
        k32.CloseHandle.argtypes = (wintypes.HANDLE,)
        k32.CloseHandle.restype = wintypes.BOOL
        self._ctypes = ctypes
        self._k32 = k32
        self._processus: list[int] = []

        job = k32.CreateJobObjectW(None, None)
        if not job:
            raise MoteurInjoignable(f"CreateJobObjectW : erreur {ctypes.get_last_error()}")
        self._job: int | None = job
        infos = _Etendue()
        infos.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not k32.SetInformationJobObject(job, 9, ctypes.byref(infos), ctypes.sizeof(infos)):
            erreur = ctypes.get_last_error()
            self.fermer()
            raise MoteurInjoignable(f"SetInformationJobObject : erreur {erreur}")

    def rattacher(self, pid: int) -> None:
        k32 = self._k32
        processus = k32.OpenProcess(0x0100 | 0x0001, False, pid)  # SET_QUOTA | TERMINATE
        if not processus:
            raise MoteurInjoignable(f"OpenProcess : erreur {self._ctypes.get_last_error()}")
        self._processus.append(processus)
        if not k32.AssignProcessToJobObject(self._job, processus):
            raise MoteurInjoignable(
                f"AssignProcessToJobObject : erreur {self._ctypes.get_last_error()}"
            )

    def fermer(self) -> None:
        """Ferme les handles ; la fermeture du job tue les processus qui y restent."""
        for processus in self._processus:
            self._k32.CloseHandle(processus)
        self._processus.clear()
        if self._job:
            self._k32.CloseHandle(self._job)
            self._job = None


class LlamaServer:
    """Gestionnaire de contexte : démarre llama-server à l'entrée, l'arrête à la sortie."""

    def __init__(
        self,
        binaire: Path,
        gguf: Path,
        ctx: int,
        threads: int,
        delai_s: float,
        journal: Path,
    ) -> None:
        self._binaire = binaire
        self._gguf = gguf
        self._ctx = ctx
        self._threads = threads
        self._delai_s = delai_s
        self._journal_chemin = journal
        self._journal: IO[bytes] | None = None
        self._processus: subprocess.Popen[bytes] | None = None
        self._job: _JobWindows | None = None
        self._port = 0

    @property
    def base_url(self) -> str:
        return f"http://{HOTE}:{self._port}/v1"

    @property
    def pid(self) -> int:
        if self._processus is None:
            raise RuntimeError("llama-server n'est pas démarré")
        return self._processus.pid

    def __enter__(self) -> "LlamaServer":
        try:
            self._demarrer()
        except BaseException:
            self._arreter()
            raise
        return self

    def __exit__(
        self,
        type_: type[BaseException] | None,
        valeur: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        self._arreter()

    def _demarrer(self) -> None:
        self._journal_chemin.parent.mkdir(parents=True, exist_ok=True)
        self._journal = self._journal_chemin.open("ab")
        if sys.platform == "win32":
            self._job = _JobWindows()
        for essai in (1, 2):
            self._lancer()
            if self._attendre():
                return
            if essai == 1 and self._processus is not None and self._processus.poll() is not None:
                _log.warning(
                    "llama-server s'est arrêté au démarrage ; nouvel essai sur un autre port"
                )
                continue
            break
        code = self._processus.poll() if self._processus is not None else None
        if code is not None:
            raise MoteurInjoignable(
                f"llama-server s'est arrêté au démarrage (code {code}) ; "
                f"voir {self._journal_chemin}"
            )
        raise MoteurInjoignable(
            f"llama-server non prêt après {self._delai_s} s ; voir {self._journal_chemin}"
        )

    def _lancer(self) -> None:
        if self._processus is not None:
            self._processus.wait(DELAI_ARRET_S)  # essai précédent, déjà arrêté
        self._port = port_libre()
        commande = [
            str(self._binaire),
            "-m",
            str(self._gguf),
            "--host",
            HOTE,
            "--port",
            str(self._port),
            "-c",
            str(self._ctx),
            "-t",
            str(self._threads),
            "--parallel",
            "1",
            "--no-webui",
            "--jinja",
        ]
        try:
            self._processus = subprocess.Popen(
                commande,
                stdin=subprocess.DEVNULL,
                stdout=self._journal,
                stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError as erreur:
            raise MoteurInjoignable(f"llama-server non lancé ({erreur})") from erreur
        if self._job is not None:
            self._job.rattacher(self._processus.pid)

    def _attendre(self) -> bool:
        """True si /health répond 200 dans le délai ; False si le délai passe ou si le processus
        meurt."""
        assert self._processus is not None
        limite = time.monotonic() + self._delai_s
        url = f"http://{HOTE}:{self._port}/health"
        with httpx.Client(trust_env=False, timeout=2.0) as client:
            while time.monotonic() < limite:
                if self._processus.poll() is not None:
                    return False
                try:
                    if client.get(url).status_code == 200:
                        return True
                except httpx.HTTPError:
                    pass
                time.sleep(PAS_ATTENTE_S)
        return False

    def _arreter(self) -> None:
        """`terminate()`, `wait(5)`, `kill()`, puis fermeture des handles."""
        processus, self._processus = self._processus, None
        if processus is not None:
            if processus.poll() is None:
                processus.terminate()
                try:
                    processus.wait(DELAI_ARRET_S)
                except subprocess.TimeoutExpired:
                    processus.kill()
                    processus.wait(DELAI_ARRET_S)
        if self._job is not None:
            self._job.fermer()
            self._job = None
        if self._journal is not None:
            self._journal.close()
            self._journal = None
