"""Routeur des pages HTML et du jeton CSRF (contrats §18, §26, §30)."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response

from waveaudit.application import composition
from waveaudit.application import lots as lots_app
from waveaudit.application.lot import dossier_lot_existant
from waveaudit.interfaces.web.commun import erreur, page

routeur = APIRouter()


@routeur.get("/", response_class=HTMLResponse)
def accueil(request: Request) -> HTMLResponse:
    config = request.app.state.config
    occupation = request.app.state.verrou.occupation()
    # [revue A3] Lecture seule : aucun GET n'écrit sur le disque.
    a_des_lots = bool(lots_app.lister_lots(config, occupation))
    return page(
        request,
        "index.html",
        {
            "modeles": composition.modeles_installes(config),
            "langue_defaut": config.fiches.langue,
            "occupation": occupation,
            "a_des_lots": a_des_lots,
        },
    )


@routeur.get("/lots", response_class=HTMLResponse)
def page_lots(request: Request) -> HTMLResponse:
    config = request.app.state.config
    lots = lots_app.lister_lots(config, request.app.state.verrou.occupation())
    return page(request, "lots.html", {"lots": lots})


@routeur.get("/lots/{id_lot}", response_class=HTMLResponse, response_model=None)
def page_lot(request: Request, id_lot: str) -> HTMLResponse | Response:
    config = request.app.state.config
    if dossier_lot_existant(id_lot, config) is None:
        return erreur(404, "lot_inconnu", "Lot inconnu.")
    return page(request, "lot.html", {"id_lot": id_lot})


@routeur.get("/api/jeton")
def jeton(request: Request) -> JSONResponse:
    """Jeton CSRF courant [revue E25] : relu par le JS après un 403 `csrf_invalide`."""
    return JSONResponse({"jeton": request.app.state.jeton_csrf})
