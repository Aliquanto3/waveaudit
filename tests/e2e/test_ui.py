"""Interface web locale de bout en bout (contrats §18, AD-2, AD-9, AD-14), faux moteur."""

import time
from pathlib import Path

from docx import Document
from fastapi.testclient import TestClient

from waveaudit.application.config import racine_projet
from waveaudit.interfaces.web.app import creer_app

DEMO = racine_projet() / "donnees" / "demo" / "notes"
_RACINE_WEB = Path(__file__).resolve().parents[2] / "src" / "waveaudit" / "interfaces" / "web"


def _vers(config, fm):
    return config.model_copy(
        update={"moteur": config.moteur.model_copy(update={"base_url": fm.base_url})}
    )


def _notes_demo() -> list[tuple[str, tuple[str, bytes]]]:
    return [
        ("notes", (chemin.name, chemin.read_bytes()))
        for chemin in sorted(DEMO.iterdir())
        if chemin.is_file()
    ]


def _attendre_fin(client: TestClient, id_lot: str, timeout_s: float = 10.0) -> dict:
    limite = time.monotonic() + timeout_s
    while True:
        reponse = client.get(f"/lots/{id_lot}/etat")
        assert reponse.status_code == 200
        donnees = reponse.json()
        if donnees["etat"] != "en_cours":
            return donnees
        if time.monotonic() > limite:
            raise AssertionError(f"lot {id_lot} toujours en cours après {timeout_s}s")
        time.sleep(0.05)


def test_bandeau_sur_chaque_page(config_test):
    client = TestClient(creer_app(config_test))
    accueil = client.get("/")
    assert accueil.status_code == 200
    assert "Démonstration — données fictives" in accueil.text

    lot = client.get("/lots/un-identifiant")
    assert lot.status_code == 200
    assert "Démonstration — données fictives" in lot.text


def test_aucune_url_externe_dans_templates_et_static():
    for chemin in (_RACINE_WEB / "templates").iterdir():
        texte = chemin.read_text(encoding="utf-8")
        assert "http://" not in texte and "https://" not in texte, chemin
    for chemin in (_RACINE_WEB / "static").iterdir():
        texte = chemin.read_text(encoding="utf-8")
        for motif in ("http://", "https://"):
            for occurrence in _occurrences(texte, motif):
                assert occurrence.startswith(("http://127.0.0.1", "https://127.0.0.1")), chemin


def _occurrences(texte: str, motif: str) -> list[str]:
    resultat = []
    depart = 0
    while True:
        index = texte.find(motif, depart)
        if index == -1:
            return resultat
        resultat.append(texte[index : index + 40])
        depart = index + 1


def test_lot_nominal_20_notes_puis_telechargement(config_test):
    client = TestClient(creer_app(config_test))
    reponse = client.post("/lots", files=_notes_demo(), follow_redirects=False)
    assert reponse.status_code == 303
    id_lot = reponse.headers["location"].rsplit("/", 1)[-1]

    etat = _attendre_fin(client, id_lot)
    assert etat["etat"] == "termine"
    assert etat["erreur"] is None
    assert etat["evenements"][0]["type"] == "lot_demarre"
    assert etat["evenements"][-1]["type"] == "lot_termine"

    telechargement = client.get(f"/lots/{id_lot}/rapport.docx")
    assert telechargement.status_code == 200
    chemin = config_test.chemins.var / "telecharge.docx"
    chemin.write_bytes(telechargement.content)
    Document(str(chemin))  # lève si le .docx est invalide


def test_second_envoi_pendant_un_lot_refuse_sans_ecriture(config_test, faux_moteur):
    lent = _vers(config_test, faux_moteur("lent"))
    client = TestClient(creer_app(lent))
    premier = client.post("/lots", files=_notes_demo()[:1], follow_redirects=False)
    assert premier.status_code == 303
    id_lot = premier.headers["location"].rsplit("/", 1)[-1]

    entrees_avant = list((lent.chemins.var / "entrees").iterdir())
    second = client.post("/lots", files=_notes_demo()[:1], follow_redirects=False)
    assert second.status_code == 409
    assert list((lent.chemins.var / "entrees").iterdir()) == entrees_avant
    _attendre_fin(client, id_lot)


def test_noms_refuses(config_test):
    client = TestClient(creer_app(config_test))
    note_valide = _notes_demo()[0]
    entrees = config_test.chemins.var / "entrees"

    cas = [
        [("notes", ("../x.md", b"contenu"))],
        [("notes", ("CON.md", b"contenu"))],
        [("notes", ("A.md", b"un")), ("notes", ("a.MD", b"deux"))],
        [("notes", ("virus.exe", b"contenu"))],
        [("notes", ("trop-gros.md", b"x" * (1024 * 1024 + 1)))],
    ]
    for fichiers in cas:
        reponse = client.post("/lots", files=fichiers, follow_redirects=False)
        assert reponse.status_code == 400, fichiers
        assert not entrees.is_dir() or not list(entrees.iterdir())

    # Un envoi valide reste accepté après ces refus (verrou bien relâché).
    reponse = client.post("/lots", files=[note_valide], follow_redirects=False)
    assert reponse.status_code == 303


def test_host_etranger_refuse(config_test):
    client = TestClient(creer_app(config_test))
    reponse = client.get("/", headers={"host": "evil.example.com"})
    assert reponse.status_code == 400


def test_origin_etranger_refuse_sur_post(config_test):
    client = TestClient(creer_app(config_test))
    entrees = config_test.chemins.var / "entrees"
    reponse = client.post(
        "/lots",
        files=[_notes_demo()[0]],
        headers={"origin": "http://evil.example.com"},
        follow_redirects=False,
    )
    assert reponse.status_code == 403
    assert not entrees.is_dir() or not list(entrees.iterdir())


def test_rapport_avant_la_fin_et_lot_inconnu(config_test, faux_moteur):
    lent = _vers(config_test, faux_moteur("lent"))
    client = TestClient(creer_app(lent))
    reponse = client.post("/lots", files=_notes_demo()[:1], follow_redirects=False)
    id_lot = reponse.headers["location"].rsplit("/", 1)[-1]

    avant_fin = client.get(f"/lots/{id_lot}/rapport.docx")
    assert avant_fin.status_code == 409
    _attendre_fin(client, id_lot)

    inconnu = client.get("/lots/jamais-vu/rapport.docx")
    assert inconnu.status_code == 404
    inconnu_etat = client.get("/lots/jamais-vu/etat")
    assert inconnu_etat.status_code == 404
