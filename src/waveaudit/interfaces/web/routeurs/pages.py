"""Routeur des pages HTML et du jeton CSRF (contrats §18, §26)."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from waveaudit.interfaces.web.commun import page

routeur = APIRouter()


@routeur.get("/", response_class=HTMLResponse)
def accueil(request: Request) -> HTMLResponse:
    return page(request, "index.html")


@routeur.get("/lots/{id_lot}", response_class=HTMLResponse)
def page_lot(request: Request, id_lot: str) -> HTMLResponse:
    return page(request, "lot.html", {"id_lot": id_lot})


@routeur.get("/api/jeton")
def jeton(request: Request) -> JSONResponse:
    """Jeton CSRF courant [revue E25] : relu par le JS après un 403 `csrf_invalide`."""
    return JSONResponse({"jeton": request.app.state.jeton_csrf})
