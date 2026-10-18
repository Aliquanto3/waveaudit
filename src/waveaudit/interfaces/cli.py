"""Interface en ligne de commande (contrats §19).

Le script `waveaudit` pointe sur `main()`, qui reconfigure la console en UTF-8 puis lance
`app` ; les tests appellent `app` directement (`typer.testing.CliRunner`).

Aucun import d'adaptateur au niveau module (contrats §12) : les commandes les importent à
l'intérieur de leur fonction, après l'activation du garde réseau le cas échéant.

Codes retour (contrats §4) : 0 lot terminé, 2 entrée/configuration invalide (dont `--modele`
inconnu ou `catalogue verifier` en échec), 3 moteur injoignable (sonde), 4 connexion interdite,
permission refusée sur `-o`, ou toute autre erreur, 5 empreinte d'artefact invalide.
"""

import logging
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from importlib.metadata import version as version_paquet
from pathlib import Path
from typing import NoReturn

import typer

from waveaudit.domaine.modeles import Langue

_log = logging.getLogger(__name__)

app = typer.Typer(help="WaveAudit : notes brutes vers fiches de vulnérabilité, hors ligne.")
catalogue_app = typer.Typer(help="Opérations sur le catalogue de constats types (contrats §15).")
app.add_typer(catalogue_app, name="catalogue")


@app.callback()
def principal() -> None:
    """WaveAudit : notes brutes vers fiches de vulnérabilité, hors ligne."""


@app.command()
def version() -> None:
    """Affiche la version installée."""
    typer.echo(f"waveaudit {version_paquet('waveaudit')}")


def _echouer(message: str, code: int) -> NoReturn:
    """Affiche un message d'une ligne sur stderr, sans trace, puis quitte avec `code`."""
    typer.echo(message, err=True)
    raise typer.Exit(code=code)


def _charger_config(chemin: Path | None = None):  # noqa: ANN201 - Configuration, import tardif
    """`application.config.charger_configuration`, erreurs traduites en code 2."""
    from waveaudit.application.config import charger_configuration
    from waveaudit.domaine.erreurs import ConfigurationInvalide

    try:
        return charger_configuration(chemin)
    except ConfigurationInvalide as erreur:
        _echouer(str(erreur), 2)


@contextmanager
def _codes_retour(commande: str) -> Iterator[None]:
    """Traduit les erreurs du bloc en codes retour (contrats §4), message d'une ligne, trace
    dans `logging`. `typer.Exit` (sous-classe d'`Exception`) est relancée telle quelle."""
    from waveaudit.application.lot import sans_chemin
    from waveaudit.domaine.erreurs import (
        ConfigurationInvalide,
        ConnexionInterdite,
        EmpreinteInvalide,
        EntreeInvalide,
        MoteurInjoignable,
    )

    try:
        yield
    except typer.Exit:
        raise
    except (EntreeInvalide, ConfigurationInvalide) as erreur:
        _echouer(sans_chemin(str(erreur)), 2)
    except MoteurInjoignable as erreur:
        _echouer(str(erreur), 3)
    except ConnexionInterdite as erreur:
        _echouer(str(erreur), 4)
    except EmpreinteInvalide as erreur:
        _echouer(str(erreur), 5)
    except PermissionError as erreur:
        _log.exception("%s : accès refusé", commande)
        # os.replace(provisoire, cible) : `filename2` est la cible, `filename` le provisoire.
        nom = erreur.filename2 or erreur.filename
        cible = Path(nom).name if nom else ""
        _echouer(f"{commande} : accès refusé en écriture ou en lecture ({cible})", 4)
    except Exception as erreur:  # erreurs httpx, OSError, CalledProcessError...
        _log.exception("%s : échec", commande)
        _echouer(f"{commande} : échec ({sans_chemin(str(erreur))})", 4)


def _module_optionnel(nom: str):  # noqa: ANN201 - module | None, import tardif
    """Importe `nom` ; `None` s'il n'existe pas encore (fonctionnalité d'une story ultérieure)."""
    import importlib

    try:
        return importlib.import_module(nom)
    except ModuleNotFoundError as erreur:
        if erreur.name == nom:
            return None
        raise


@app.command()
def installer(
    candidats: bool = typer.Option(
        False, "--candidats", help="Télécharge aussi les modèles candidats du manifeste"
    ),
) -> None:
    """Télécharge et vérifie les artefacts du manifeste (contrats §11)."""
    config = _charger_config()
    from waveaudit.installation import manifeste, telechargement

    with _codes_retour("installer"):
        artefacts = manifeste.charger(config.chemins.manifeste)
        telechargement.installer(artefacts, config.chemins.var, candidats)
    typer.echo("installation terminée")


@app.command()
def fiches(
    dossier: Path = typer.Argument(..., help="Dossier contenant les notes (.md, .txt)"),
    o: Path | None = typer.Option(
        None, "-o", help="Copie supplémentaire du rapport Word, en plus de var/sorties/<id>/"
    ),
    modele: str | None = typer.Option(
        None, "--modele", help="Nom du modèle (manifeste en local-gere, modele_api en externe)"
    ),
    config: Path | None = typer.Option(
        None, "--config", help="Fichier de configuration TOML supplémentaire"
    ),
    langue: Langue | None = typer.Option(
        None, "--langue", help="Langue des fiches et du rapport Word (défaut : config)"
    ),
) -> None:
    """Traite les notes d'un dossier et produit un rapport de fiches de vulnérabilité."""
    cfg = _charger_config(config)

    from waveaudit.securite.garde_reseau import garde

    with garde(cfg.reseau.hotes_autorises):
        from waveaudit.adaptateurs.export_docx import BANDEAU
        from waveaudit.application.lot import executer_lot
        from waveaudit.domaine.modeles import EvenementLot, RequeteLot, Statut, TypeEvenement

        typer.echo(BANDEAU)

        def abonne(evenement: EvenementLot) -> None:
            if evenement.type not in (
                TypeEvenement.FICHE_TERMINEE,
                TypeEvenement.FICHE_NON_TRAITEE,
                TypeEvenement.FICHE_NON_RATTACHEE,
            ):
                return
            duree = round(evenement.duree_s or 0.0)
            typer.echo(
                f"[{evenement.index}/{evenement.total}] {evenement.note} : "
                f"{evenement.statut} ({duree} s)"
            )

        with _codes_retour("fiches"):
            resultat = executer_lot(
                RequeteLot(dossier=dossier, modele=modele, copie_rapport=o, langue=langue),
                cfg,
                abonne,
            )

        ok = sum(1 for f in resultat.rapport.fiches if f.statut == Statut.OK)
        a_revoir = len(resultat.rapport.fiches) - ok
        typer.echo(
            f"{ok} fiche(s) ok, {a_revoir} à revoir, "
            f"{len(resultat.rapport.ecartees)} entrée(s) écartée(s) ; "
            f"rapport : {resultat.chemin_rapport}"
        )
        typer.echo(BANDEAU)


@app.command()
def incident(
    dossier: Path = typer.Argument(..., help="Dossier contenant les journaux (CERT)"),
    o: Path | None = typer.Option(
        None, "-o", help="Copie supplémentaire du rapport Word, en plus de var/sorties/<id>/"
    ),
    annee: int | None = typer.Option(
        None, "--annee", help="Année des journaux sans année explicite (par défaut : courante)"
    ),
    modele: str | None = typer.Option(
        None, "--modele", help="Nom du modèle (manifeste en local-gere, modele_api en externe)"
    ),
    config: Path | None = typer.Option(
        None, "--config", help="Fichier de configuration TOML supplémentaire"
    ),
) -> None:
    """Analyse un dossier de journaux et produit un rapport d'incident (CERT, contrats §21)."""
    from datetime import datetime

    cfg = _charger_config(config)
    annee_effective = annee if annee is not None else datetime.now().year

    from waveaudit.securite.garde_reseau import garde

    with garde(cfg.reseau.hotes_autorises):
        from waveaudit.adaptateurs.export_docx import BANDEAU
        from waveaudit.application.incident import executer_incident
        from waveaudit.domaine.incident import RequeteIncident
        from waveaudit.domaine.modeles import EvenementLot, Statut, TypeEvenement

        typer.echo(BANDEAU)

        def abonne(evenement: EvenementLot) -> None:
            if evenement.type != TypeEvenement.FICHE_TERMINEE:
                return
            duree = round(evenement.duree_s or 0.0)
            typer.echo(
                f"[{evenement.index}/{evenement.total}] {evenement.note} : "
                f"{evenement.statut} ({duree} s)"
            )

        with _codes_retour("incident"):
            if modele and cfg.moteur.mode == "local-gere":
                # Sans détection, le moteur n'est jamais ouvert : le nom est vérifié ici
                # pour que `--modele` inconnu donne toujours le code 2 (contrats §4, §19).
                from waveaudit.application.composition import choisir_modele
                from waveaudit.installation import manifeste

                choisir_modele(cfg, manifeste.charger(cfg.chemins.manifeste), modele)
            resultat = executer_incident(
                RequeteIncident(
                    dossier=dossier,
                    annee=annee_effective,
                    modele=modele,
                    copie_rapport=o,
                ),
                cfg,
                abonne,
            )

        ok = sum(1 for r in resultat.rapport.recits if r.statut == Statut.OK)
        a_revoir = len(resultat.rapport.recits) - ok
        typer.echo(
            f"{ok} récit(s) ok, {a_revoir} à revoir ; "
            f"rapport : {resultat.chemin_rapport.name} (lot {resultat.id_lot})"
        )
        typer.echo(BANDEAU)


@app.command()
def ui(
    port: int | None = typer.Option(
        None, "--port", min=1, max=65535, help="Port d'écoute (remplace la config)"
    ),
    config: Path | None = typer.Option(
        None, "--config", help="Fichier de configuration TOML supplémentaire"
    ),
) -> None:
    """Démarre l'interface web locale (contrats §18)."""
    cfg = _charger_config(config)
    if port is not None:
        cfg = cfg.model_copy(update={"ui": cfg.ui.model_copy(update={"port": port})})

    from waveaudit.securite.garde_reseau import garde

    with garde(cfg.reseau.hotes_autorises):
        if cfg.ui.hote not in ("127.0.0.1", "::1"):
            _echouer(f"ui.hote doit être 127.0.0.1 ou ::1 (reçu {cfg.ui.hote!r})", 2)
        import uvicorn

        from waveaudit.interfaces.web.app import creer_app

        with _codes_retour("ui"):
            try:
                uvicorn.run(creer_app(cfg), host=cfg.ui.hote, port=cfg.ui.port)
            except SystemExit as sortie:  # uvicorn quitte par sys.exit(1) si le port est pris
                if sortie.code not in (0, None):
                    _echouer(f"ui : démarrage impossible sur le port {cfg.ui.port} (occupé ?)", 4)


@catalogue_app.command("verifier")
def catalogue_verifier(
    config: Path | None = typer.Option(
        None, "--config", help="Fichier de configuration TOML supplémentaire"
    ),
) -> None:
    """Contrôle le catalogue de constats types (contrats §15, §16)."""
    cfg = _charger_config(config)
    from waveaudit.adaptateurs.catalogue_yaml import verifier

    erreurs = verifier(cfg.chemins.catalogue)
    if erreurs:
        for erreur in erreurs:
            typer.echo(erreur, err=True)
        raise typer.Exit(code=2)
    typer.echo("catalogue valide")


@app.command()
def banc(
    dossier: Path = typer.Argument(..., help="Dossier contenant les notes (.md, .txt)"),
    modele: str | None = typer.Option(None, "--modele", help="Nom du modèle (manifeste)"),
    langue: Langue | None = typer.Option(
        None, "--langue", help="Langue des fiches du lot mesuré (défaut : config)"
    ),
    seed: int | None = typer.Option(
        None,
        "--seed",
        min=0,
        max=2**32 - 1,
        help="Seed du moteur pour ce banc, de 0 à 2**32-1 (défaut : config)",
    ),
) -> None:
    """Exécute un lot instrumenté (mémoire, durées, recopie) — contrats §20, §29."""
    cfg = _charger_config()

    from waveaudit.securite.garde_reseau import garde

    with garde(cfg.reseau.hotes_autorises):
        module = _module_optionnel("waveaudit.application.banc")
        if module is None:
            _echouer("banc : disponible en story 15", 2)
        with _codes_retour("banc"):
            module.executer_banc(dossier, cfg, modele, langue, seed)


@app.command()
def exporter(
    lot: str = typer.Argument(..., help="Identifiant du lot (var/sorties/<id>/)"),
    brouillon: bool = typer.Option(
        False, "--brouillon", help="Exporte le brouillon (défaut : rapport final)"
    ),
    config: Path | None = typer.Option(
        None, "--config", help="Fichier de configuration TOML supplémentaire"
    ),
) -> None:
    """Exporte en Word le rapport final ou le brouillon d'un lot (contrats §27, CAP-13, CAP-17)."""
    cfg = _charger_config(config)
    mode = "brouillon" if brouillon else "final"

    from waveaudit.securite.garde_reseau import garde

    with garde(cfg.reseau.hotes_autorises):
        from waveaudit.adaptateurs.export_docx import BANDEAU
        from waveaudit.application.export import exporter_lot

        typer.echo(BANDEAU)
        with _codes_retour("exporter"):
            try:
                chemin, non_validees = exporter_lot(cfg, lot, mode)
            except PermissionError as erreur:
                # [revue X2] §27 : code 4, « fermez le document dans Word ».
                _log.exception("exporter : accès refusé")
                nom = erreur.filename2 or erreur.filename
                cible = Path(nom).name if nom else ""
                _echouer(f"exporter : accès refusé ({cible}), fermez le document dans Word", 4)
        typer.echo(f"rapport : {chemin.name} (lot {lot})")
        if mode == "final" and non_validees:
            typer.echo(f"fiches non validées : {non_validees} (exclues, listées en annexe)")
        typer.echo(BANDEAU)


@app.command()
def sbom() -> None:
    """Écrit le SBOM de l'environnement installé (contrats §11)."""
    config = _charger_config()
    from waveaudit.installation import sbom as sbom_module

    with _codes_retour("sbom"):
        chemin = sbom_module.generer(config.chemins.var)
    typer.echo(f"sbom écrit : {chemin}")


def main() -> None:
    """Point d'entrée du script `waveaudit` (contrats §19)."""
    for flux in (sys.stdout, sys.stderr):
        reconfigurer = getattr(flux, "reconfigure", None)
        if reconfigurer is not None:
            reconfigurer(encoding="utf-8", errors="replace")
    app()
