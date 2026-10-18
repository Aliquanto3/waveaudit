"""Interface web locale de bout en bout (contrats §18, §26, AD-2, AD-9, AD-14, AD-22)."""

import re
import time
from pathlib import Path

from docx import Document
from fastapi.testclient import TestClient

from tests.web_outils import client as client_web
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
    client = client_web(config_test)
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
    client = client_web(config_test)
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
    client = client_web(lent)
    premier = client.post("/lots", files=_notes_demo()[:1], follow_redirects=False)
    assert premier.status_code == 303
    id_lot = premier.headers["location"].rsplit("/", 1)[-1]

    entrees_avant = list((lent.chemins.var / "entrees").iterdir())
    second = client.post("/lots", files=_notes_demo()[:1], follow_redirects=False)
    assert second.status_code == 409
    assert second.json()["code"] == "lot_en_cours"
    assert list((lent.chemins.var / "entrees").iterdir()) == entrees_avant
    _attendre_fin(client, id_lot)


def test_noms_refuses(config_test):
    client = client_web(config_test)
    note_valide = _notes_demo()[0]
    entrees = config_test.chemins.var / "entrees"

    cas = [
        [("notes", ("../x.md", b"contenu"))],
        [("notes", ("CON.md", b"contenu"))],
        [("notes", ("A.md", b"un")), ("notes", ("a.MD", b"deux"))],
        [("notes", ("virus.exe", b"contenu"))],
    ]
    for fichiers in cas:
        reponse = client.post("/lots", files=fichiers, follow_redirects=False)
        assert reponse.status_code == 400, fichiers
        assert reponse.json()["code"] == "nom_refuse", fichiers
        assert not entrees.is_dir() or not list(entrees.iterdir())

    # Un envoi valide reste accepté après ces refus (verrou bien relâché).
    reponse = client.post("/lots", files=[note_valide], follow_redirects=False)
    assert reponse.status_code == 303


def test_host_etranger_refuse(config_test):
    client = client_web(config_test)
    reponse = client.get("/", headers={"host": "evil.example.com"})
    assert reponse.status_code == 400
    assert reponse.json()["code"] == "hote_refuse"


def test_origin_etranger_refuse_sur_post(config_test):
    client = client_web(config_test)
    entrees = config_test.chemins.var / "entrees"
    reponse = client.post(
        "/lots",
        files=[_notes_demo()[0]],
        headers={"origin": "http://evil.example.com"},
        follow_redirects=False,
    )
    assert reponse.status_code == 403
    assert reponse.json()["code"] == "origine_refusee"
    assert not entrees.is_dir() or not list(entrees.iterdir())


def test_rapport_avant_la_fin_et_lot_inconnu(config_test, faux_moteur):
    lent = _vers(config_test, faux_moteur("lent"))
    client = client_web(lent)
    reponse = client.post("/lots", files=_notes_demo()[:1], follow_redirects=False)
    id_lot = reponse.headers["location"].rsplit("/", 1)[-1]

    avant_fin = client.get(f"/lots/{id_lot}/rapport.docx")
    assert avant_fin.status_code == 409
    assert avant_fin.json()["code"] == "lot_non_termine"
    _attendre_fin(client, id_lot)

    inconnu = client.get("/lots/jamais-vu/rapport.docx")
    assert inconnu.status_code == 404
    assert inconnu.json()["code"] == "lot_inconnu"
    inconnu_etat = client.get("/lots/jamais-vu/etat")
    assert inconnu_etat.status_code == 404
    assert inconnu_etat.json()["code"] == "lot_inconnu"


def test_multipart_malforme_relache_le_verrou(config_test):
    client = client_web(config_test)
    malforme = client.post("/lots", content=b"zzz", headers={"content-type": "multipart/form-data"})
    assert malforme.status_code == 400
    assert malforme.json()["code"] == "corps_invalide"
    reponse = client.post("/lots", files=[_notes_demo()[0]], follow_redirects=False)
    assert reponse.status_code == 303
    _attendre_fin(client, reponse.headers["location"].rsplit("/", 1)[-1])


def test_noms_reserves_windows_avec_point_ou_espace(config_test):
    client = client_web(config_test)
    for nom in ("CON.x.md", "NUL .md", "aux.b.txt", "LPT1.a.md", "COM1 .txt"):
        reponse = client.post("/lots", files=[("notes", (nom, b"x"))], follow_redirects=False)
        assert reponse.status_code == 400, nom
        assert reponse.json()["code"] == "nom_refuse", nom


def test_host_ipv6_boucle_locale_accepte(config_test):
    client = client_web(config_test)
    reponse = client.get("/", headers={"host": f"[::1]:{config_test.ui.port}"})
    assert reponse.status_code == 200


def test_etat_depuis_ne_renvoie_que_les_nouveaux_evenements(config_test):
    client = client_web(config_test)
    reponse = client.post("/lots", files=_notes_demo()[:2], follow_redirects=False)
    id_lot = reponse.headers["location"].rsplit("/", 1)[-1]
    complet = _attendre_fin(client, id_lot)["evenements"]
    assert len(complet) > 2
    suite = client.get(f"/lots/{id_lot}/etat", params={"depuis": 2}).json()["evenements"]
    assert suite == complet[2:]
    negatif = client.get(f"/lots/{id_lot}/etat", params={"depuis": -1})
    assert negatif.status_code == 422
    assert negatif.json()["code"] == "requete_invalide"


# --- Socle web v2 : enveloppe de sécurité commune et erreurs codées (contrats §26, AD-22) ---

MIO = 1024 * 1024
_EN_TETES_SECURITE = {
    "content-security-policy": (
        "default-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
    ),
    "x-content-type-options": "nosniff",
    "referrer-policy": "no-referrer",
}
_CHEMIN_WINDOWS = re.compile(r"[A-Za-z]:[\\/]")
_SCRIPT_EN_LIGNE = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>", re.IGNORECASE)


def _aucune_entree(config) -> bool:
    entrees = config.chemins.var / "entrees"
    return not entrees.is_dir() or not list(entrees.iterdir())


def _erreur_codee(reponse, statut: int, code: str) -> dict:
    assert reponse.status_code == statut, reponse.text
    corps = reponse.json()
    assert corps["code"] == code
    assert isinstance(corps["detail"], str) and corps["detail"]
    return corps


def test_post_sans_jeton_ou_avec_mauvais_jeton_refuse(config_test):
    app = creer_app(config_test, hotes_test=("testserver",))
    nu = TestClient(app)
    sans = nu.post("/lots", files=[_notes_demo()[0]], follow_redirects=False)
    _erreur_codee(sans, 403, "csrf_invalide")
    mauvais = nu.post(
        "/lots",
        files=[_notes_demo()[0]],
        headers={"X-CSRF-Token": app.state.jeton_csrf + "x"},
        follow_redirects=False,
    )
    _erreur_codee(mauvais, 403, "csrf_invalide")
    # Le jeton est propre à chaque instance : celui d'une autre application est refusé.
    autre = creer_app(config_test, hotes_test=("testserver",)).state.jeton_csrf
    assert autre != app.state.jeton_csrf
    reponse = nu.post(
        "/lots", files=[_notes_demo()[0]], headers={"X-CSRF-Token": autre}, follow_redirects=False
    )
    _erreur_codee(reponse, 403, "csrf_invalide")
    assert _aucune_entree(config_test)


def test_post_sans_longueur_411(config_test):
    client = client_web(config_test)

    def morceaux():
        yield b"--x\r\n"

    reponse = client.post(
        "/lots", content=morceaux(), headers={"content-type": "multipart/form-data; boundary=x"}
    )
    _erreur_codee(reponse, 411, "longueur_requise")
    assert _aucune_entree(config_test)


def test_limite_par_fichier_et_totale(config_test):
    client = client_web(config_test)
    par_fichier = client.post(
        "/lots", files=[("notes", ("trop-gros.md", b"x" * (MIO + 1)))], follow_redirects=False
    )
    corps = _erreur_codee(par_fichier, 413, "trop_volumineux")
    assert corps["limite"] == "fichier"
    assert corps["detail"] == (
        "Ce fichier dépasse 1 Mo (trop-gros.md, 1,0 Mo). Réduisez-le ou retirez-le du dépôt."
    )

    # 21 notes de 1 Mio : chacune respecte la limite par fichier, le dépôt dépasse 20 Mio.
    notes = [("notes", (f"n{i}.md", b"x" * MIO)) for i in range(21)]
    total = client.post("/lots", files=notes, follow_redirects=False)
    corps = _erreur_codee(total, 413, "trop_volumineux")
    assert corps["limite"] == "total"
    assert corps["detail"].startswith("Le dépôt dépasse 20 Mo au total (21,0 Mo).")
    assert _aucune_entree(config_test)

    # Limite totale de 256 Kio sur les autres écritures.
    autre = client.post("/autre", content=b"x" * (256 * 1024 + 1))
    assert _erreur_codee(autre, 413, "trop_volumineux")["limite"] == "total"

    # Le verrou est relâché : un envoi valide passe ensuite.
    reponse = client.post("/lots", files=[_notes_demo()[0]], follow_redirects=False)
    assert reponse.status_code == 303
    _attendre_fin(client, reponse.headers["location"].rsplit("/", 1)[-1])


def test_trop_de_fichiers(config_test):
    client = client_web(config_test)
    notes = [("notes", (f"n{i}.md", b"x")) for i in range(101)]
    reponse = client.post("/lots", files=notes, follow_redirects=False)
    corps = _erreur_codee(reponse, 400, "trop_de_fichiers")
    assert corps["detail"] == "Le dépôt compte 101 fichiers ; 100 au plus par lot."
    assert _aucune_entree(config_test)


def test_nom_termine_par_point_ou_espace_refuse(config_test):
    client = client_web(config_test)
    for nom in ("a.md.", "a.md ", "b.txt..", "c.md. "):
        reponse = client.post("/lots", files=[("notes", (nom, b"x"))], follow_redirects=False)
        _erreur_codee(reponse, 400, "nom_refuse")
    assert _aucune_entree(config_test)


def test_doublon_apres_normalisation_refuse(config_test):
    client = client_web(config_test)
    for premier, second in (("A.md", "a.md "), ("Note.TXT", "note.txt"), ("x.md", "X.md.")):
        fichiers = [("notes", (premier, b"un")), ("notes", (second, b"deux"))]
        reponse = client.post("/lots", files=fichiers, follow_redirects=False)
        _erreur_codee(reponse, 400, "nom_refuse")
    assert _aucune_entree(config_test)


def test_aucune_note_refusee(config_test):
    client = client_web(config_test)
    reponse = client.post("/lots", files=[("autre", ("a.md", b"x"))], follow_redirects=False)
    _erreur_codee(reponse, 400, "aucune_note")


def test_testserver_refuse_sans_hotes_test(config_test):
    reponse = TestClient(creer_app(config_test)).get("/")
    _erreur_codee(reponse, 400, "hote_refuse")


def test_host_en_capitales_accepte(config_test):
    client = client_web(config_test)
    for hote in (f"LOCALHOST:{config_test.ui.port}", f"LocalHost:{config_test.ui.port}"):
        assert client.get("/", headers={"host": hote}).status_code == 200, hote
    assert client.get("/", headers={"host": "TESTSERVER"}).status_code == 200


def test_api_jeton(config_test):
    app = creer_app(config_test, hotes_test=("testserver",))
    reponse = TestClient(app).get("/api/jeton")
    assert reponse.status_code == 200
    assert reponse.json() == {"jeton": app.state.jeton_csrf}
    assert reponse.headers["cache-control"] == "no-store"


def test_pages_portent_le_jeton_sans_script_ni_style_en_ligne(config_test):
    app = creer_app(config_test, hotes_test=("testserver",))
    client = client_web(app)
    for chemin in ("/", "/lots/un-identifiant"):
        texte = client.get(chemin).text
        assert f'<meta name="csrf" content="{app.state.jeton_csrf}">' in texte, chemin
        assert '<html lang="fr">' in texte
        assert _SCRIPT_EN_LIGNE.search(texte) is None, chemin
        assert re.search(r"\son\w+\s*=", texte, re.IGNORECASE) is None, chemin
        assert re.search(r"\sstyle\s*=", texte, re.IGNORECASE) is None, chemin
        assert texte.count("Démonstration — données fictives") == 2, chemin
    for chemin in (_RACINE_WEB / "templates").iterdir():
        source = chemin.read_text(encoding="utf-8")
        assert _SCRIPT_EN_LIGNE.search(source) is None, chemin
        assert re.search(r"<style", source, re.IGNORECASE) is None, chemin


def test_csp_et_nosniff_sur_chaque_reponse(config_test):
    client = client_web(config_test)
    reponses = {
        "accueil": client.get("/"),
        "page lot": client.get("/lots/un-identifiant"),
        "statique": client.get("/static/style.css"),
        "jeton": client.get("/api/jeton"),
        "etat inconnu": client.get("/lots/jamais-vu/etat"),
        "route inconnue": client.get("/nulle-part"),
        "hote refuse": client.get("/", headers={"host": "evil.example.com"}),
        "csrf": client.post("/lots", headers={"X-CSRF-Token": "faux"}, content=b"x"),
        "origine": client.post("/lots", headers={"origin": "http://evil.example"}, content=b"x"),
    }
    for nom, reponse in reponses.items():
        for en_tete, valeur in _EN_TETES_SECURITE.items():
            assert reponse.headers.get(en_tete) == valeur, (nom, en_tete)
        type_contenu = reponse.headers.get("content-type", "")
        if type_contenu.startswith(("application/json", "text/html")):
            assert reponse.headers.get("cache-control") == "no-store", nom


def test_corps_d_erreur_codes_sans_chemin_absolu(config_test, tmp_path):
    client = client_web(config_test)
    serveur = [
        client.get("/nulle-part"),
        client.post("/"),
        client.get("/lots/x/etat", params={"depuis": "abc"}),
        client.get("/lots/x/rapport.docx"),
        client.post("/lots", files=[("notes", ("../x.md", b"x"))]),
        client.post("/lots", content=b"zzz", headers={"content-type": "multipart/form-data"}),
        client.get("/", headers={"host": "evil.example.com"}),
    ]
    for reponse in serveur:
        corps = reponse.json()
        assert set(corps) >= {"detail", "code"}, corps
        assert isinstance(corps["detail"], str) and isinstance(corps["code"], str), corps
        assert str(tmp_path) not in reponse.text
        assert str(config_test.chemins.var) not in reponse.text
        assert _CHEMIN_WINDOWS.search(corps["detail"]) is None, corps
