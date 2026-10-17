"""Vrai llama-server et vrais poids (marqueur `slow`, sauté si `var/modeles` est absent)."""

import httpx
import pytest

from waveaudit.adaptateurs.llama_server import LlamaServer
from waveaudit.application.config import charger_configuration
from waveaudit.installation import manifeste

pytestmark = pytest.mark.slow


def test_vrai_llama_server_demarre_et_s_arrete(tmp_path):
    config = charger_configuration()
    var = config.chemins.var
    artefacts = manifeste.charger(config.chemins.manifeste)
    binaire = manifeste.chemin(manifeste.par_role(artefacts, "moteur"), var)
    gguf = manifeste.chemin(manifeste.par_role(artefacts, "modele_defaut"), var)
    if not (var / "modeles").is_dir() or not binaire.is_file() or not gguf.is_file():
        pytest.skip("var/modeles ou llama-server absent : lancer `waveaudit installer`")
    m = config.moteur
    journal = tmp_path / "llama-server-reel.log"  # jamais dans le var/ du dépôt
    with LlamaServer(binaire, gguf, m.ctx, m.threads, m.delai_demarrage_s, journal) as serveur:
        reponse = httpx.get(serveur.base_url + "/models", trust_env=False, timeout=10)
        assert reponse.status_code == 200
