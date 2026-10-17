"""Interface en ligne de commande (contrats §19). Socle : seule la commande `version` existe.

Aucun import d'adaptateur au niveau module (contrats §12) : les commandes les importent à
l'intérieur de leur fonction, après l'activation du garde réseau.
"""

from importlib.metadata import version as version_paquet

import typer

app = typer.Typer(help="WaveAudit : notes brutes vers fiches de vulnérabilité, hors ligne.")


@app.callback()
def principal() -> None:
    """WaveAudit : notes brutes vers fiches de vulnérabilité, hors ligne."""


@app.command()
def version() -> None:
    """Affiche la version installée."""
    typer.echo(f"waveaudit {version_paquet('waveaudit')}")
