"""Interface en ligne de commande (contrats §19). Socle : seule la commande `version` existe.

Le script `waveaudit` pointe sur `main()`, qui reconfigure la console en UTF-8 puis lance
`app` ; les tests appellent `app` directement (`typer.testing.CliRunner`).

Aucun import d'adaptateur au niveau module (contrats §12) : les commandes les importent à
l'intérieur de leur fonction, après l'activation du garde réseau.
"""

import sys
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


def main() -> None:
    """Point d'entrée du script `waveaudit` (contrats §19)."""
    for flux in (sys.stdout, sys.stderr):
        reconfigurer = getattr(flux, "reconfigure", None)
        if reconfigurer is not None:
            reconfigurer(encoding="utf-8", errors="replace")
    app()
