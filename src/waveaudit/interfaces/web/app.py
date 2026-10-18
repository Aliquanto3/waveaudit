"""Interface web locale (contrats §18, §26, AD-2, AD-14, AD-22).

`creer_app(config)` assemble les routeurs par surface (`routeurs/`) sous une enveloppe de
sécurité commune, sans activer le garde réseau (contrats §12, AD-9) : c'est à l'appelant (la
commande CLI `ui`, interfaces/cli.py) d'activer `securite.garde_reseau` puis de lancer uvicorn
sur `config.ui.hote`/`config.ui.port` (`127.0.0.1` ou `::1` seulement), `uvicorn` et les
adaptateurs étant réservés à `interfaces/cli.py` et `application/composition.py` (contrats §12,
`tests/unitaires/test_architecture.py`).

Les stories web suivantes remplissent leur module de routeur sans retoucher ce fichier
(AD-22 [revue A28]).
"""

import asyncio
import logging
import secrets
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from waveaudit.application.moteur_demande import MoteurALaDemande, VerrouUnique
from waveaudit.domaine.configuration import Configuration
from waveaudit.interfaces.web.commun import BANDEAU, RACINE, en_mo, erreur
from waveaudit.interfaces.web.routeurs import incidents, lots, pages, relecture, theme

__all__ = ["BANDEAU", "creer_app"]

# [v2] §24 [revue E3] : à l'arrêt, le lifespan attend la fin de l'usage en cours (verrou) avant
# de fermer le moteur, 10 s au plus.
ATTENTE_ARRET_MOTEUR_S = 10.0

MIO = 1024 * 1024
# Limites totales de corps par route d'écriture (§26) ; les autres écritures : 256 Kio.
_LIMITES = {"/lots": 20 * MIO, "/incidents": 50 * MIO}
_LIMITE_PAR_DEFAUT = 256 * 1024
# Origin et jeton CSRF : toute méthode non sûre (DELETE, PATCH compris, au-delà du §26).
_METHODES_SURES = frozenset({"GET", "HEAD", "OPTIONS"})
# Longueur et taille : écritures à corps du §26.
_ECRITURES = frozenset({"POST", "PUT"})

_journal = logging.getLogger(__name__)

_EN_TETES = {
    "Content-Security-Policy": (
        "default-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}

_CODES_HTTP = {
    404: ("introuvable", "Ressource introuvable."),
    405: ("methode_refusee", "Méthode non permise sur cette adresse."),
}


def _hotes_autorises(port: int, hotes_test: tuple[str, ...]) -> frozenset[str]:
    """Hôtes acceptés (§26) : boucle locale avec le port, sans port si le port vaut 80.

    `[::1]:<port>` : en-tête Host envoyé par le navigateur quand `ui.hote` vaut `::1`.
    """
    noms = ("127.0.0.1", "localhost", "[::1]")
    hotes = {f"{nom}:{port}" for nom in noms}
    if port == 80:
        hotes |= set(noms)
    return frozenset(hotes | {hote.lower() for hote in hotes_test})


def _refus_taille(chemin: str, taille: int, limite: int) -> Response:
    if chemin == "/lots":
        detail = (
            f"Le dépôt dépasse 20 Mo au total ({en_mo(taille)}). "
            "Déposez les notes en plusieurs lots."
        )
    elif chemin == "/incidents":
        detail = (
            f"Le dépôt dépasse 50 Mo au total ({en_mo(taille)}). "
            "Déposez les journaux en plusieurs lots."
        )
    else:
        detail = f"La requête dépasse {limite // 1024} Ko ({taille // 1024} Ko)."
    return erreur(413, "trop_volumineux", detail, limite="total")


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    # [revue E3] Attente bornée de la fin de l'usage en cours (régénération, ou lot/incident qui
    # tourne encore), puis fermeture du moteur ; une entrée restée en_cours est ensuite lue comme
    # interrompue (§25, §30).
    limite = time.monotonic() + ATTENTE_ARRET_MOTEUR_S
    while app.state.verrou.occupation() is not None and time.monotonic() < limite:
        await asyncio.sleep(0.05)
    app.state.moteur.fermer()


def creer_app(config: Configuration, *, hotes_test: tuple[str, ...] = ()) -> FastAPI:
    """Construit l'application web (contrats §26). N'active pas le garde réseau.

    `hotes_test` n'est renseigné que par `tests/web_outils.py` (`("testserver",)`) ; la
    commande `ui` appelle `creer_app(config)` [revue A7/E27].
    """
    app = FastAPI(title="WaveAudit", lifespan=_lifespan)
    app.state.jeton_csrf = secrets.token_urlsafe(32)
    app.state.config = config
    # [v2] §24 : un seul `VerrouUnique` et un seul `MoteurALaDemande` par processus UI.
    app.state.verrou = VerrouUnique()
    app.state.moteur = MoteurALaDemande(config)
    hotes_autorises = _hotes_autorises(config.ui.port, hotes_test)
    origines_autorisees = frozenset(f"http://{hote}" for hote in hotes_autorises)

    def _controler(request: Request) -> Response | None:
        """Règles communes, dans l'ordre du §26 ; renvoie la réponse de refus ou `None`."""
        if request.headers.get("host", "").lower() not in hotes_autorises:
            return erreur(400, "hote_refuse", "Hôte non autorisé.")
        if request.method in _METHODES_SURES:
            return None
        origine = request.headers.get("origin")
        if origine is not None and origine.lower() not in origines_autorisees:
            return erreur(403, "origine_refusee", "Origine non autorisée.")
        jeton = request.headers.get("x-csrf-token", "")
        if not secrets.compare_digest(jeton.encode("utf-8"), app.state.jeton_csrf.encode("utf-8")):
            return erreur(
                403,
                "csrf_invalide",
                "Jeton de sécurité absent ou périmé. Rechargez la page.",
            )
        if request.method not in _ECRITURES:
            return None
        longueur = request.headers.get("content-length", "")
        if not longueur.isascii() or not longueur.isdigit():
            return erreur(411, "longueur_requise", "Longueur de la requête requise.")
        limite = _LIMITES.get(request.url.path, _LIMITE_PAR_DEFAUT)
        if int(longueur) > limite:
            return _refus_taille(request.url.path, int(longueur), limite)
        return None

    @app.middleware("http")
    async def _enveloppe(request: Request, call_next) -> Response:
        reponse = _controler(request)
        if reponse is None:
            try:
                reponse = await call_next(request)
            except Exception:
                # Sans cela, ServerErrorMiddleware répondrait en texte brut, sans les en-têtes
                # de sécurité ni code ; la trace reste dans le journal local, pas dans la réponse.
                _journal.exception("Erreur interne sur %s %s", request.method, request.url.path)
                reponse = erreur(500, "erreur_interne", "Erreur interne du serveur.")
        for nom, valeur in _EN_TETES.items():
            reponse.headers[nom] = valeur
        if not request.url.path.startswith("/static/"):
            # HTML compris [revue E25] : une page en cache garderait un jeton CSRF périmé.
            reponse.headers["Cache-Control"] = "no-store"
        return reponse

    @app.exception_handler(StarletteHTTPException)
    async def _erreur_http(request: Request, exc: StarletteHTTPException) -> Response:
        code, detail = _CODES_HTTP.get(exc.status_code, ("erreur_http", "Requête refusée."))
        return erreur(exc.status_code, code, detail)

    @app.exception_handler(RequestValidationError)
    async def _erreur_validation(request: Request, exc: RequestValidationError) -> Response:
        return erreur(422, "requete_invalide", "Paramètres de requête invalides.")

    app.mount("/static", StaticFiles(directory=RACINE / "static"), name="static")
    for module in (pages, lots, relecture, incidents, theme):
        app.include_router(module.routeur)
    return app
