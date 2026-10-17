"""`LlamaServer` contre un faux binaire Python (contrats §10, AD-11). Jamais le vrai llama-server.

L'interpréteur lancé est `sys._base_executable` : sous Windows, le `python.exe` d'un venv est
un lanceur qui crée lui-même un processus enfant, ce qui fausserait le pid et l'arrêt.
"""

import json
import sys
import time
from pathlib import Path

import httpx
import psutil
import pytest

from waveaudit.adaptateurs.llama_server import LlamaServer
from waveaudit.domaine.erreurs import MoteurInjoignable

TESTS = Path(__file__).resolve().parents[1]
PYTHON = Path(getattr(sys, "_base_executable", sys.executable))
FAUX = Path("faux_llama_server")  # passé en `-m` : nom du module du faux binaire


@pytest.fixture
def faux_binaire(monkeypatch, tmp_path):
    monkeypatch.setenv("PYTHONPATH", str(TESTS))
    monkeypatch.setenv("FAUX_LLAMA_MARQUEUR", str(tmp_path / "marqueur"))

    def fabrique(scenario: str = "nominal", delai_s: float = 15.0) -> LlamaServer:
        monkeypatch.setenv("FAUX_LLAMA_SCENARIO", scenario)
        return LlamaServer(PYTHON, FAUX, 2048, 2, delai_s, tmp_path / "journaux" / "ls.log")

    return fabrique


def _attendre_fin(pid: int, delai_s: float = 10.0) -> bool:
    limite = time.monotonic() + delai_s
    while time.monotonic() < limite:
        if not psutil.pid_exists(pid) or psutil.Process(pid).status() == psutil.STATUS_ZOMBIE:
            return True
        time.sleep(0.1)
    return False


def _arguments(journal: Path) -> list[str]:
    lignes = [ligne for ligne in journal.read_text().splitlines() if ligne.startswith("ARGS ")]
    return json.loads(lignes[-1][5:])


def test_demarrage_port_local_arguments_et_arret(faux_binaire, tmp_path):
    serveur = faux_binaire()
    with serveur:
        pid = serveur.pid
        assert serveur.base_url.startswith("http://127.0.0.1:")
        assert serveur.base_url.endswith("/v1")
        reponse = httpx.get(serveur.base_url + "/models", trust_env=False)
        assert reponse.status_code == 200
        assert psutil.pid_exists(pid)
    assert _attendre_fin(pid)
    args = _arguments(tmp_path / "journaux" / "ls.log")
    port = serveur.base_url.split(":")[2].split("/")[0]
    assert args[args.index("--host") + 1] == "127.0.0.1"
    assert args[args.index("--port") + 1] == port
    assert args[args.index("-c") + 1] == "2048"
    assert args[args.index("-t") + 1] == "2"
    assert {"--parallel", "--no-webui", "--jinja"} <= set(args)


def test_mort_au_demarrage_un_seul_nouvel_essai(faux_binaire, tmp_path):
    serveur = faux_binaire("meurt_une_fois")
    with serveur:
        assert httpx.get(serveur.base_url + "/models", trust_env=False).status_code == 200
    assert len(_lignes_args(tmp_path)) == 2


def test_mort_deux_fois_moteur_injoignable(faux_binaire, tmp_path):
    with pytest.raises(MoteurInjoignable, match="arrêté"):
        with faux_binaire("meurt"):
            pass
    assert len(_lignes_args(tmp_path)) == 2


def test_delai_depasse_moteur_injoignable_et_processus_arrete(faux_binaire, monkeypatch):
    lances: list[int] = []
    original = LlamaServer._lancer

    def lancer(soi):
        original(soi)
        lances.append(soi.pid)

    monkeypatch.setattr(LlamaServer, "_lancer", lancer)
    with pytest.raises(MoteurInjoignable, match="non prêt"):
        with faux_binaire("jamais_pret", delai_s=1.0):
            pass
    assert len(lances) == 1
    assert _attendre_fin(lances[0])


def test_binaire_absent_moteur_injoignable(tmp_path):
    serveur = LlamaServer(tmp_path / "absent.exe", FAUX, 2048, 2, 1.0, tmp_path / "j.log")
    with pytest.raises(MoteurInjoignable):
        with serveur:
            pass


@pytest.mark.skipif(sys.platform != "win32", reason="Job Object : Windows seulement")
def test_job_object_tue_l_enfant_a_la_fermeture(faux_binaire):
    serveur = faux_binaire()
    with serveur:
        pid = serveur.pid
        assert psutil.pid_exists(pid)
        serveur._job.fermer()  # fermeture du dernier handle du job : KILL_ON_JOB_CLOSE
        serveur._job = None
        assert _attendre_fin(pid, 5.0)


def _lignes_args(tmp_path: Path) -> list[str]:
    texte = (tmp_path / "journaux" / "ls.log").read_text()
    return [ligne for ligne in texte.splitlines() if ligne.startswith("ARGS ")]
