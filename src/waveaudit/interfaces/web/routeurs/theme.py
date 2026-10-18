"""Routeur du thème (contrats §28) : `GET /theme/logo.svg`, logo privé optionnel.

Sert `config.chemins.theme_prive / "web" / "logo.svg"` s'il existe (relu à chaque requête),
sinon 404 `logo_absent`. Aucun autre fichier de `theme-prive/` n'est servi.
"""

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, Response

from waveaudit.interfaces.web.commun import chemin_logo, erreur

routeur = APIRouter()


@routeur.get("/theme/logo.svg")
def logo(request: Request) -> Response:
    chemin = chemin_logo(request)
    if not chemin.is_file():
        return erreur(404, "logo_absent", "Aucun logo privé n'est présent.")
    return FileResponse(chemin, media_type="image/svg+xml")
