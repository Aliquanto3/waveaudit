"""Client de test de l'interface web (contrats §26, AD-22).

`client(config)` crée l'application avec `hotes_test=("testserver",)` ; `client(app)` reprend
une application déjà créée (par exemple celle de la commande `ui`, sans `testserver` : passer
alors `base_url="http://127.0.0.1:<port>"`). Dans les deux cas, chaque requête porte
`X-CSRF-Token` lu dans `app.state.jeton_csrf`.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from waveaudit.domaine.configuration import Configuration
from waveaudit.interfaces.web.app import creer_app

HOTES_TEST = ("testserver",)


def application(config: Configuration) -> FastAPI:
    """Application de test : `testserver` accepté comme hôte."""
    return creer_app(config, hotes_test=HOTES_TEST)


def client(cible: Configuration | FastAPI, *, base_url: str = "http://testserver") -> TestClient:
    """Client qui pose le jeton CSRF de l'application sur chaque requête."""
    app = cible if isinstance(cible, FastAPI) else application(cible)
    return TestClient(app, base_url=base_url, headers={"X-CSRF-Token": app.state.jeton_csrf})
