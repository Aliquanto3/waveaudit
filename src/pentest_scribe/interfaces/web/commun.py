"""Outils partagés des routeurs web (contrats §26, AD-22) : gabarits, pages, erreurs codées."""

from pathlib import Path
from typing import Any

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

# Copie du bandeau d'`adaptateurs.export_docx.BANDEAU` : interfaces/web/ ne peut importer aucun
# adaptateur, même dans une fonction (contrats §12, test_architecture.py).
BANDEAU = "Démonstration — données fictives"

RACINE = Path(__file__).resolve().parent
gabarits = Jinja2Templates(directory=RACINE / "templates")


def chemin_logo(request: Request) -> Path:
    """Chemin du logo privé (§28) : `<theme_prive>/web/logo.svg`, relu à chaque appel."""
    config = request.app.state.config
    return Path(config.chemins.theme_prive) / "web" / "logo.svg"


def page(request: Request, nom: str, contexte: dict[str, Any] | None = None) -> HTMLResponse:
    """Rend un gabarit avec le bandeau (AD-14), le jeton CSRF (§26) et `logo_present` (§28).

    `logo_present` est recalculé à chaque rendu par `is_file()` (jamais mis en cache) : un
    logo ajouté ou retiré de `theme-prive/web/` sur le disque est vu à la requête suivante.
    """
    complet = {
        "bandeau": BANDEAU,
        "jeton_csrf": request.app.state.jeton_csrf,
        "logo_present": chemin_logo(request).is_file(),
    }
    return gabarits.TemplateResponse(request, nom, complet | (contexte or {}))


def erreur(statut: int, code: str, detail: str, **champs: Any) -> JSONResponse:
    """Erreur JSON `{"detail", "code"}` (§26), plus les champs propres au code."""
    return JSONResponse({"detail": detail, "code": code} | champs, status_code=statut)


def en_mo(octets: int) -> str:
    """Taille en Mo à une décimale, virgule française : `2,4 Mo` (EXPERIENCE, Voice and Tone)."""
    return f"{octets / (1024 * 1024):.1f}".replace(".", ",") + " Mo"
