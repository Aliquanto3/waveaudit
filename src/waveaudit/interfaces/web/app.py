"""Interface web locale (contrats §18, AD-2, AD-14).

`creer_app(config)` construit l'application sans activer le garde réseau (contrats §12, AD-9) :
c'est à l'appelant (la commande CLI `ui`, interfaces/cli.py) d'activer `securite.garde_reseau`
puis de lancer uvicorn sur `config.ui.hote`/`config.ui.port` (`127.0.0.1` ou `::1` seulement),
`uvicorn` et les adaptateurs étant réservés à `interfaces/cli.py` et `application/composition.py`
(contrats §12, `tests/unitaires/test_architecture.py`).
"""

import re
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Query, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.datastructures import UploadFile as UploadFileBrut

from waveaudit.application.lot import RAPPORT, executer_lot, nouvel_id_lot
from waveaudit.domaine.configuration import Configuration
from waveaudit.domaine.modeles import EvenementLot, RequeteLot

# Copie du bandeau d'`adaptateurs.export_docx.BANDEAU` : interfaces/web/ ne peut importer aucun
# adaptateur, même dans une fonction (contrats §12, test_architecture.py).
BANDEAU = "Démonstration — données fictives"

_RACINE = Path(__file__).resolve().parent
_TAILLE_MAX_OCTETS = 1024 * 1024  # 1 Mo (contrats §18)
_MOTIF_NOM = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]{0,99}\.(md|txt)$", re.IGNORECASE)
_RESERVES_WINDOWS = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)

EtatStr = Literal["en_cours", "termine", "echoue"]


class NomRefuse(Exception):
    """Nom de fichier de note refusé (contrats §18) : donne HTTP 400 à l'appelant."""


@dataclass
class _EtatLot:
    etat: EtatStr = "en_cours"
    evenements: list[dict] = field(default_factory=list)
    erreur: str | None = None


class _RegistreLots:
    """État de chaque lot lancé par l'UI, protégé par un verrou (contrats §18)."""

    def __init__(self) -> None:
        self._verrou = threading.Lock()
        self._etats: dict[str, _EtatLot] = {}

    def creer(self, id_lot: str) -> None:
        with self._verrou:
            self._etats[id_lot] = _EtatLot()

    def abonne(self, id_lot: str):
        def recevoir(evenement: EvenementLot) -> None:
            with self._verrou:
                etat = self._etats.get(id_lot)
                if etat is not None:
                    etat.evenements.append(evenement.model_dump(mode="json"))

        return recevoir

    def terminer(self, id_lot: str) -> None:
        with self._verrou:
            etat = self._etats.get(id_lot)
            if etat is not None:
                etat.etat = "termine"

    def echouer(self, id_lot: str, message: str) -> None:
        with self._verrou:
            etat = self._etats.get(id_lot)
            if etat is not None:
                etat.etat = "echoue"
                etat.erreur = message

    def lire(self, id_lot: str, depuis: int = 0) -> _EtatLot | None:
        """Copie de l'état ; `depuis` ne copie que les événements à partir de cet indice."""
        with self._verrou:
            etat = self._etats.get(id_lot)
            if etat is None:
                return None
            return _EtatLot(etat=etat.etat, evenements=etat.evenements[depuis:], erreur=etat.erreur)


def _valider_nom(nom_brut: str, deja_vus: set[str]) -> str:
    """Vérifie un nom de note (contrats §18) ; lève `NomRefuse` sinon renvoie le nom normalisé.

    `base != nom_brut` refuse un nom qui contient un composant de chemin (`../x.md`), puisque
    `Path(nom_brut).name` en retire alors une partie.
    """
    base = Path(nom_brut).name
    if base != nom_brut or not _MOTIF_NOM.fullmatch(base):
        raise NomRefuse(f"nom de fichier refusé : {nom_brut!r}")
    # Windows résout le périphérique sur la partie avant le premier point, espaces finaux
    # retirés : `CON.x.md` et `NUL .md` sont réservés comme `CON.md`.
    if base.split(".", 1)[0].rstrip(" ").upper() in _RESERVES_WINDOWS:
        raise NomRefuse(f"nom de fichier réservé (Windows) : {nom_brut!r}")
    cle = base.casefold()
    if cle in deja_vus:
        raise NomRefuse(f"nom de fichier en double : {nom_brut!r}")
    deja_vus.add(cle)
    return base


async def _valider_notes(fichiers: list[UploadFile]) -> list[tuple[str, bytes]]:
    """Valide et lit chaque note envoyée (contrats §18) ; lève `NomRefuse` au premier refus."""
    if not fichiers:
        raise NomRefuse("aucune note envoyée")
    deja_vus: set[str] = set()
    resultat: list[tuple[str, bytes]] = []
    for fichier in fichiers:
        nom = _valider_nom(fichier.filename or "", deja_vus)
        contenu = await fichier.read(_TAILLE_MAX_OCTETS + 1)
        if len(contenu) > _TAILLE_MAX_OCTETS:
            raise NomRefuse(f"note trop volumineuse (> 1 Mo) : {nom!r}")
        resultat.append((nom, contenu))
    return resultat


def creer_app(config: Configuration) -> FastAPI:
    """Construit l'application web (contrats §18). N'active pas le garde réseau."""
    app = FastAPI(title="WaveAudit")
    app.mount("/static", StaticFiles(directory=_RACINE / "static"), name="static")
    gabarits = Jinja2Templates(directory=_RACINE / "templates")
    registre = _RegistreLots()
    verrou_post = threading.Lock()
    port = config.ui.port
    # `[::1]:<port>` : en-tête Host envoyé par le navigateur quand `ui.hote` vaut `::1`
    # (permis par contrats §18, absent de sa liste d'hôtes ; écart consigné dans la spec).
    hotes_autorises = {f"127.0.0.1:{port}", f"localhost:{port}", f"[::1]:{port}", "testserver"}
    origines_autorisees = {f"http://{hote}" for hote in hotes_autorises}

    @app.middleware("http")
    async def _garde_hote_origine(request: Request, call_next):
        hote = request.headers.get("host", "")
        if hote not in hotes_autorises:
            return JSONResponse({"detail": "hôte non autorisé"}, status_code=400)
        if request.method == "POST":
            origine = request.headers.get("origin")
            if origine is not None and origine not in origines_autorisees:
                return JSONResponse({"detail": "origine non autorisée"}, status_code=403)
        return await call_next(request)

    def _executer_en_fond(id_lot: str, dossier_entree: Path) -> None:
        try:
            try:
                requete = RequeteLot(dossier=dossier_entree, id_lot=id_lot)
                executer_lot(requete, config, registre.abonne(id_lot))
                registre.terminer(id_lot)
            except Exception as erreur:  # noqa: BLE001 - reporté à l'état du lot, pas relevé
                registre.echouer(id_lot, str(erreur))
        finally:
            verrou_post.release()

    @app.get("/", response_class=HTMLResponse)
    def accueil(request: Request) -> HTMLResponse:
        return gabarits.TemplateResponse(request, "index.html", {"bandeau": BANDEAU})

    @app.post("/lots")
    async def creer_lot(request: Request) -> RedirectResponse:
        if not verrou_post.acquire(blocking=False):
            return JSONResponse({"detail": "un lot est déjà en cours"}, status_code=409)
        # Toute sortie avant le démarrage du thread (multipart malformé, refus, erreur disque)
        # relâche le verrou ; ensuite c'est le `finally` du thread qui le relâche.
        lance = False
        try:
            formulaire = await request.form()
            notes = [v for v in formulaire.getlist("notes") if isinstance(v, UploadFileBrut)]
            try:
                fichiers = await _valider_notes(notes)
            except NomRefuse as erreur:
                return JSONResponse({"detail": str(erreur)}, status_code=400)
            id_lot = nouvel_id_lot(config.chemins.var)
            dossier_entree = config.chemins.var / "entrees" / id_lot
            dossier_entree.mkdir(parents=True, exist_ok=True)
            for nom, contenu in fichiers:
                (dossier_entree / nom).write_bytes(contenu)
            registre.creer(id_lot)
            fil = threading.Thread(
                target=_executer_en_fond, args=(id_lot, dossier_entree), daemon=True
            )
            try:
                fil.start()
            except RuntimeError as erreur:
                registre.echouer(id_lot, str(erreur))
                raise
            lance = True
            return RedirectResponse(f"/lots/{id_lot}", status_code=303)
        finally:
            if not lance:
                verrou_post.release()

    @app.get("/lots/{id_lot}", response_class=HTMLResponse)
    def page_lot(request: Request, id_lot: str) -> HTMLResponse:
        return gabarits.TemplateResponse(
            request, "lot.html", {"bandeau": BANDEAU, "id_lot": id_lot}
        )

    @app.get("/lots/{id_lot}/etat")
    def etat_lot(id_lot: str, depuis: int = Query(0, ge=0)) -> JSONResponse:
        # `depuis` (facultatif) : le JS ne redemande que les nouveaux événements à chaque
        # interrogation, sans recopier tout le journal du lot ; 0 donne la réponse complète.
        etat = registre.lire(id_lot, depuis)
        if etat is None:
            return JSONResponse({"detail": "lot inconnu"}, status_code=404)
        return JSONResponse(
            {
                "id_lot": id_lot,
                "etat": etat.etat,
                "evenements": etat.evenements,
                "erreur": etat.erreur,
            }
        )

    @app.get("/lots/{id_lot}/rapport.docx")
    def rapport_lot(id_lot: str) -> FileResponse:
        etat = registre.lire(id_lot)
        if etat is None:
            return JSONResponse({"detail": "lot inconnu"}, status_code=404)
        if etat.etat != "termine":
            return JSONResponse({"detail": "lot non terminé"}, status_code=409)
        chemin = config.chemins.var / "sorties" / id_lot / RAPPORT
        if not chemin.is_file():
            return JSONResponse({"detail": "rapport introuvable"}, status_code=404)
        return FileResponse(
            chemin,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=RAPPORT,
        )

    return app
