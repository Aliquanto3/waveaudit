"""Verrou unique et moteur à la demande (contrats §24, AD-20) : sans vrai llama-server."""

import threading
import time
from datetime import datetime

import pytest

from tests.unitaires.test_composition import GO, _FauxServeur, _installer, _local
from waveaudit.adaptateurs import memoire_psutil
from waveaudit.application import composition
from waveaudit.application.moteur_demande import MoteurALaDemande, Occupation, VerrouUnique
from waveaudit.domaine.erreurs import ConfigurationInvalide, MoteurInjoignable
from waveaudit.installation import manifeste

DEBUT = datetime(2026, 1, 2, 3, 4, 5)
BINAIRE = "llama-server-b11714"
MODELE_A = "granite-4.0-1b-q4km"
MODELE_B = "qwen3-1.7b-q4km"


def _attendre(condition, delai_s: float = 5.0) -> bool:
    """Sondage borné, jamais de sleep fixe long."""
    fin = time.monotonic() + delai_s
    while time.monotonic() < fin:
        if condition():
            return True
        time.sleep(0.01)
    return condition()


def _avec_inactivite(config, inactivite_s):
    return config.model_copy(
        update={"ui": config.ui.model_copy(update={"inactivite_moteur_s": inactivite_s})}
    )


# --- VerrouUnique ---


def test_prendre_non_bloquant():
    verrou = VerrouUnique()
    occupation = Occupation("fiches", "lot-1", None, DEBUT)
    assert verrou.prendre(occupation)
    resultats: list[bool] = []
    fil = threading.Thread(
        target=lambda: resultats.append(verrou.prendre(Occupation("incident", "x", None, DEBUT))),
        daemon=True,
    )
    fil.start()
    fil.join(timeout=2)
    assert resultats == [False]
    assert verrou.occupation() == occupation
    verrou.liberer()
    assert verrou.occupation() is None
    assert verrou.prendre(Occupation("regeneration", "lot-1", 2, DEBUT))


def test_occupation_copiee():
    verrou = VerrouUnique()
    occupation = Occupation("regeneration", "lot-1", 3, DEBUT)
    verrou.prendre(occupation)
    lue = verrou.occupation()
    assert lue == occupation
    assert lue is not occupation
    assert lue is not verrou.occupation()


def test_definir_remplace_occupation_provisoire():
    verrou = VerrouUnique()
    with pytest.raises(RuntimeError):
        verrou.definir(Occupation("fiches", "lot-1", None, DEBUT))
    assert verrou.occupation() is None
    assert verrou.prendre(Occupation("fiches", "", None, DEBUT))
    definitive = Occupation("fiches", "20260102-030405", None, DEBUT)
    verrou.definir(definitive)
    assert verrou.occupation() == definitive
    assert not verrou.prendre(Occupation("incident", "autre", None, DEBUT))


# --- MoteurALaDemande, local-gere avec _FauxServeur ---


@pytest.fixture
def local(config_test, faux_moteur, monkeypatch):
    """(fabrique de configuration, serveurs) : _FauxServeur dirigé vers un faux moteur."""
    serveurs: list[_FauxServeur] = []
    urls = {"url": config_test.moteur.base_url}

    class Serveur(_FauxServeur):
        def __init__(self, *args):
            super().__init__(*args)
            self.base_url = urls["url"]
            self.pid = len(serveurs) + 1
            self.precedents_fermes = all(not s.ouvert for s in serveurs)
            serveurs.append(self)

    monkeypatch.setattr(composition, "LlamaServer", Serveur)
    monkeypatch.setattr(memoire_psutil, "ram_disponible_octets", lambda: 16 * GO)
    artefacts = manifeste.charger(config_test.chemins.manifeste)
    defaut = manifeste.par_role(artefacts, "modele_defaut").nom
    _installer(config_test, artefacts, BINAIRE, defaut, MODELE_A, MODELE_B)

    def fabrique(inactivite_s: float = 60.0, scenario: str | None = None):
        if scenario:
            urls["url"] = faux_moteur(scenario).base_url
        return _avec_inactivite(_local(config_test), inactivite_s)

    return fabrique, serveurs, defaut


def test_reutilisation_pour_le_meme_modele(local):
    fabrique, serveurs, _ = local
    moteur = MoteurALaDemande(fabrique())
    try:
        with moteur.utiliser(MODELE_A) as (ports1, info1):
            assert info1.nom_modele == MODELE_A
        with moteur.utiliser(MODELE_A) as (ports2, info2):
            assert ports2 is ports1
            assert info2 == info1
        assert len(serveurs) == 1
        assert serveurs[0].ouvert
    finally:
        moteur.fermer()
    assert not serveurs[0].ouvert


def test_changement_de_modele_ferme_puis_ouvre(local):
    fabrique, serveurs, _ = local
    moteur = MoteurALaDemande(fabrique())
    try:
        with moteur.utiliser(MODELE_A):
            pass
        with moteur.utiliser(MODELE_B) as (_, info):
            assert info.nom_modele == MODELE_B
        assert len(serveurs) == 2
        assert serveurs[1].precedents_fermes
        assert not serveurs[0].ouvert
        assert serveurs[1].ouvert
    finally:
        moteur.fermer()


def test_echec_ouverture_referme_et_remonte(local):
    fabrique, serveurs, _ = local
    moteur = MoteurALaDemande(fabrique(scenario="injoignable"))
    try:
        with pytest.raises(MoteurInjoignable):
            with moteur.utiliser(MODELE_A):
                pytest.fail("bloc exécuté malgré l'échec de la sonde")
        assert len(serveurs) == 1
        assert not serveurs[0].ouvert
        with pytest.raises(ConfigurationInvalide):
            with moteur.utiliser("inconnu"):
                pass
        assert len(serveurs) == 1
        assert moteur._minuterie is None
    finally:
        moteur.fermer()


def test_arret_apres_inactivite(local):
    fabrique, serveurs, _ = local
    moteur = MoteurALaDemande(fabrique(inactivite_s=0.1))
    try:
        with moteur.utiliser(MODELE_A):
            pass
        assert _attendre(lambda: not serveurs[0].ouvert)
        with moteur.utiliser(MODELE_A):
            assert len(serveurs) == 2
            assert serveurs[1].ouvert
    finally:
        moteur.fermer()


def test_minuterie_rearmee(local):
    fabrique, serveurs, _ = local
    moteur = MoteurALaDemande(fabrique(inactivite_s=60.0))
    try:
        with moteur.utiliser(MODELE_A):
            pass
        premiere = moteur._minuterie
        assert premiere is not None and premiere.is_alive()
        with moteur.utiliser(MODELE_A):
            assert moteur._minuterie is None
            assert _attendre(lambda: not premiere.is_alive())
        seconde = moteur._minuterie
        assert seconde is not None and seconde is not premiere
        assert len(serveurs) == 1 and serveurs[0].ouvert
    finally:
        moteur.fermer()
    assert moteur._minuterie is None
    assert _attendre(lambda: not seconde.is_alive())


def test_fermer_idempotent(local):
    fabrique, serveurs, _ = local
    moteur = MoteurALaDemande(fabrique())
    moteur.fermer()
    with moteur.utiliser(MODELE_A):
        pass
    moteur.fermer()
    moteur.fermer()
    assert not serveurs[0].ouvert
    assert moteur._minuterie is None


def test_cle_nom_resolu(local):
    fabrique, serveurs, defaut = local
    moteur = MoteurALaDemande(fabrique())
    try:
        with moteur.utiliser(None) as (_, info):
            assert info.nom_modele == defaut
        with moteur.utiliser(defaut):
            pass
        with moteur.utiliser(None):
            pass
        assert len(serveurs) == 1
    finally:
        moteur.fermer()


def test_minuterie_concurrente_sans_fermeture_pendant_usage(local):
    fabrique, serveurs, _ = local
    moteur = MoteurALaDemande(fabrique(inactivite_s=0.01))
    erreurs: list[str] = []
    ensemble = threading.Barrier(2, timeout=5)

    def boucle(decalage: int):
        try:
            for i in range(40):
                with moteur.utiliser(MODELE_A) as (_, info):
                    serveur = serveurs[info.pid - 1]
                    for _ in range(3):
                        if not serveur.ouvert:
                            erreurs.append(f"moteur {info.pid} fermé pendant un usage")
                        time.sleep(0.002)
                # [revue M1] Pauses autour de la minuterie : des échéances tombent pendant
                # la reprise d'un usage, au lieu d'être toujours annulées avant d'échoir ;
                # toutes les 10 itérations, pause commune garantissant une échéance réelle.
                if i % 10 == 9:
                    ensemble.wait()
                    time.sleep(0.05)
                else:
                    time.sleep(0.005 * ((i + decalage) % 6))
        except Exception as exc:  # noqa: BLE001 - remonté par l'assertion
            erreurs.append(repr(exc))

    fils = [threading.Thread(target=boucle, args=(d,), daemon=True) for d in (0, 2)]
    try:
        for fil in fils:
            fil.start()
        for fil in fils:
            fil.join(timeout=30)
        assert not any(fil.is_alive() for fil in fils)
        assert erreurs == []
        assert len(serveurs) > 1, "aucune échéance réelle : le test ne prouve rien"
    finally:
        moteur.fermer()
    assert all(not s.ouvert for s in serveurs)


def test_echeance_perimee_ne_ferme_pas(local):
    """[revue M1] Rappel de minuterie déjà parti (cancel trop tard) : sans effet.

    Déterministe : appelle `_echeance` avec une minuterie annulée, pendant un usage puis
    après qu'une nouvelle minuterie a été armée.
    """
    fabrique, serveurs, _ = local
    moteur = MoteurALaDemande(fabrique(inactivite_s=60.0))
    try:
        with moteur.utiliser(MODELE_A):
            pass
        premiere = moteur._minuterie
        with moteur.utiliser(MODELE_A):
            moteur._echeance(premiere)
            assert serveurs[0].ouvert
            moteur._minuterie = premiere  # minuterie courante, mais un usage est en cours
            moteur._echeance(premiere)
            assert serveurs[0].ouvert
            moteur._minuterie = None
        seconde = moteur._minuterie
        assert seconde is not None and seconde is not premiere
        moteur._echeance(premiere)
        assert serveurs[0].ouvert and moteur._minuterie is seconde
        moteur._echeance(seconde)
        assert not serveurs[0].ouvert and moteur._minuterie is None
        seconde.cancel()
    finally:
        moteur.fermer()


# --- Mode externe ---


def test_mode_externe_sans_processus(config_test, monkeypatch):
    def interdit(*args, **kwargs):
        raise AssertionError("aucun processus en mode externe")

    monkeypatch.setattr(composition, "LlamaServer", interdit)
    moteur = MoteurALaDemande(_avec_inactivite(config_test, 60.0))
    try:
        with moteur.utiliser(None) as (ports1, info):
            assert info.pid is None
            assert info.base_url == config_test.moteur.base_url
        with moteur.utiliser(None) as (ports2, _):
            assert ports2 is ports1
        with moteur.utiliser("autre-modele") as (ports3, info3):
            assert ports3 is not ports1
            assert info3.nom_modele == "autre-modele"
    finally:
        moteur.fermer()
    moteur.fermer()
