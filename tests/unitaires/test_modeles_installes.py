"""Modèles installés pour l'UI (contrats §11, §26). Fichier séparé de `test_composition.py`
(que la story Q5 peut toucher en parallèle)."""

from pathlib import Path

from waveaudit.adaptateurs import memoire_psutil
from waveaudit.application import composition

GO = composition.OCTETS_PAR_GO


def _artefact_toml(
    nom: str, role: str, destination: str, *, duree_indicative_s: float | None = None
) -> str:
    extra = f"\nduree_indicative_s = {duree_indicative_s}" if duree_indicative_s else ""
    return f"""
[[artefact]]
nom = "{nom}"
role = "{role}"
version = "1.0"
url = "https://example.invalid/{nom}.gguf"
sha256 = "{"0" * 64}"
taille = 1000
licence = "MIT"
source = "test"
destination = "{destination}"
extraire = false
executable = ""
prefixe_systeme = ""{extra}
"""


def _manifeste(tmp_path: Path) -> Path:
    chemin = tmp_path / "artefacts.toml"
    chemin.write_text(
        _artefact_toml(
            "defaut-x", "modele_defaut", "modeles/defaut-x.gguf", duree_indicative_s=12.0
        )
        + _artefact_toml("repli-y", "modele_repli", "modeles/repli-y.gguf")
        + _artefact_toml("cand-z", "candidat", "modeles/cand-z.gguf"),
        encoding="utf-8",
    )
    return chemin


def _local(config, manifeste: Path, **moteur):
    return config.model_copy(
        update={
            "moteur": config.moteur.model_copy(update={"mode": "local-gere", **moteur}),
            "chemins": config.chemins.model_copy(update={"manifeste": manifeste}),
        }
    )


def _toucher(config, destination: str) -> None:
    chemin = config.chemins.var / destination
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_bytes(b"x" * 10)


def test_local_gere_fichiers_installes_et_defaut(config_test, tmp_path, monkeypatch):
    """Fichiers présents : les trois modèles sont listés, dans l'ordre du manifeste."""
    config = _local(config_test, _manifeste(tmp_path))
    for destination in ("modeles/defaut-x.gguf", "modeles/repli-y.gguf", "modeles/cand-z.gguf"):
        _toucher(config, destination)
    monkeypatch.setattr(memoire_psutil, "ram_disponible_octets", lambda: int(16 * GO))

    modeles = composition.modeles_installes(config)

    assert [m.nom for m in modeles] == ["defaut-x", "repli-y", "cand-z"]
    assert [m.role for m in modeles] == ["modele_defaut", "modele_repli", "candidat"]
    assert [m.defaut for m in modeles] == [True, False, False]
    assert modeles[0].duree_indicative_s == 12.0
    assert modeles[1].duree_indicative_s is None
    assert modeles[0].taille_o == 10


def test_fichiers_absents_exclus_et_defaut_au_premier_installe(config_test, tmp_path, monkeypatch):
    """Le modèle défaut choisi par RAM n'est pas installé : le premier installé le remplace."""
    config = _local(config_test, _manifeste(tmp_path))
    _toucher(config, "modeles/repli-y.gguf")  # "defaut-x" reste absent du disque
    monkeypatch.setattr(memoire_psutil, "ram_disponible_octets", lambda: int(16 * GO))

    modeles = composition.modeles_installes(config)

    assert [m.nom for m in modeles] == ["repli-y"]
    assert modeles[0].defaut is True


def test_repli_si_ram_basse(config_test, tmp_path, monkeypatch):
    """RAM basse : `modele_repli` est le défaut même si `modele_defaut` est installé."""
    config = _local(config_test, _manifeste(tmp_path))
    for destination in ("modeles/defaut-x.gguf", "modeles/repli-y.gguf"):
        _toucher(config, destination)
    monkeypatch.setattr(memoire_psutil, "ram_disponible_octets", lambda: 0)

    modeles = composition.modeles_installes(config)

    par_nom = {m.nom: m for m in modeles}
    assert par_nom["defaut-x"].defaut is False
    assert par_nom["repli-y"].defaut is True


def test_aucun_modele_installe(config_test, tmp_path, monkeypatch):
    config = _local(config_test, _manifeste(tmp_path))
    monkeypatch.setattr(memoire_psutil, "ram_disponible_octets", lambda: int(16 * GO))

    assert composition.modeles_installes(config) == []


def test_externe_une_entree(config_test):
    """Mode externe : une seule entrée, `moteur.modele_api` ou `"externe"` (§11 [revue E11])."""
    assert config_test.moteur.mode == "externe"
    modeles = composition.modeles_installes(config_test)
    assert len(modeles) == 1
    modele = modeles[0]
    assert modele.role == "externe"
    assert modele.defaut is True
    assert modele.taille_o == 0

    avec_api = config_test.model_copy(
        update={"moteur": config_test.moteur.model_copy(update={"modele_api": "mon-modele"})}
    )
    assert composition.modeles_installes(avec_api)[0].nom == "mon-modele"


def test_processus_actif(monkeypatch):
    """`processus_actif` écarte un pid réutilisé (créé après `cree_le`, §30)."""
    from datetime import datetime, timedelta

    maintenant = datetime.now().astimezone()

    monkeypatch.setattr(memoire_psutil, "date_creation_processus", lambda pid: None)
    assert composition.processus_actif(12345, maintenant) is False

    cree_avant = (maintenant - timedelta(hours=1)).timestamp()
    monkeypatch.setattr(memoire_psutil, "date_creation_processus", lambda pid: cree_avant)
    assert composition.processus_actif(12345, maintenant) is True

    cree_apres = (maintenant + timedelta(hours=1)).timestamp()
    monkeypatch.setattr(memoire_psutil, "date_creation_processus", lambda pid: cree_apres)
    assert composition.processus_actif(12345, maintenant) is False
