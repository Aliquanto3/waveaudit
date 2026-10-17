"""Interface en ligne de commande (contrats §19).

Le script `waveaudit` pointe sur `main()`, qui reconfigure la console en UTF-8 puis lance
`app` ; les tests appellent `app` directement (`typer.testing.CliRunner`).

Aucun import d'adaptateur au niveau module (contrats §12) : les commandes les importent à
l'intérieur de leur fonction, après l'activation du garde réseau le cas échéant.

Codes retour (contrats §4) : 0 lot terminé, 2 entrée/configuration invalide (dont `--modele`
inconnu ou `catalogue verifier` en échec), 3 moteur injoignable (sonde), 4 connexion interdite,
permission refusée sur `-o`, ou toute autre erreur, 5 empreinte d'artefact invalide.
"""

import sys
from importlib.metadata import version as version_paquet
from pathlib import Path
from typing import NoReturn

import typer

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
    from waveaudit.domaine.erreurs import EmpreinteInvalide
    from waveaudit.installation import manifeste, telechargement

    try:
        artefacts = manifeste.charger(config.chemins.manifeste)
        telechargement.installer(artefacts, config.chemins.var, candidats)
    except EmpreinteInvalide as erreur:
        _echouer(str(erreur), 5)
    except OSError as erreur:
        _echouer(f"erreur disque pendant l'installation : {erreur}", 4)
    except Exception as erreur:  # erreurs httpx (hors ligne, hôte injoignable, HTTP...) incluses
        _echouer(f"téléchargement impossible : {erreur}", 4)
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
) -> None:
    """Traite les notes d'un dossier et produit un rapport de fiches de vulnérabilité."""
    cfg = _charger_config(config)

    from waveaudit.securite.garde_reseau import garde

    with garde(cfg.reseau.hotes_autorises):
        from waveaudit.adaptateurs.export_docx import BANDEAU
        from waveaudit.application.lot import executer_lot
        from waveaudit.domaine.erreurs import (
            ConfigurationInvalide,
            ConnexionInterdite,
            EntreeInvalide,
            MoteurInjoignable,
        )
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

        try:
            resultat = executer_lot(
                RequeteLot(dossier=dossier, modele=modele, copie_rapport=o), cfg, abonne
            )
        except EntreeInvalide as erreur:
            _echouer(str(erreur), 2)
        except ConfigurationInvalide as erreur:
            _echouer(str(erreur), 2)
        except MoteurInjoignable as erreur:
            _echouer(str(erreur), 3)
        except ConnexionInterdite as erreur:
            _echouer(str(erreur), 4)
        except Exception as erreur:
            _echouer(f"échec du lot : {erreur}", 4)

        ok = sum(1 for f in resultat.rapport.fiches if f.statut == Statut.OK)
        a_revoir = len(resultat.rapport.fiches) - ok
        typer.echo(
            f"{ok} fiche(s) ok, {a_revoir} à revoir, "
            f"{len(resultat.rapport.ecartees)} entrée(s) écartée(s) ; "
            f"rapport : {resultat.chemin_rapport.name}"
        )
        typer.echo(BANDEAU)


@app.command()
def ui(
    port: int | None = typer.Option(None, "--port", help="Port d'écoute (remplace la config)"),
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

        uvicorn.run(creer_app(cfg), host=cfg.ui.hote, port=cfg.ui.port)


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
) -> None:
    """Exécute un lot instrumenté (mémoire, durées) — contrats §20."""
    cfg = _charger_config()

    from waveaudit.securite.garde_reseau import garde

    with garde(cfg.reseau.hotes_autorises):
        module = _module_optionnel("waveaudit.application.banc")
        if module is None:
            _echouer("banc : disponible en story 15", 2)
        module.executer_banc(dossier, cfg, modele)


@app.command()
def sbom() -> None:
    """Écrit le SBOM de l'environnement installé (contrats §11)."""
    config = _charger_config()
    from waveaudit.installation import sbom as sbom_module

    try:
        chemin = sbom_module.generer(config.chemins.var)
    except OSError as erreur:
        _echouer(f"sbom : erreur disque ({erreur})", 4)
    except Exception as erreur:  # subprocess.CalledProcessError notamment
        _echouer(f"sbom : {erreur}", 4)
    typer.echo(f"sbom écrit : {chemin}")


def main() -> None:
    """Point d'entrée du script `waveaudit` (contrats §19)."""
    for flux in (sys.stdout, sys.stderr):
        reconfigurer = getattr(flux, "reconfigure", None)
        if reconfigurer is not None:
            reconfigurer(encoding="utf-8", errors="replace")
    app()
