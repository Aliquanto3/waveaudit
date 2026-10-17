"""Génération du SBOM de l'environnement (contrats §11, AD-12)."""

import subprocess
import sys
from pathlib import Path


def generer(var: Path) -> Path:
    """Écrit `<var>/sbom.cdx.json` en analysant l'interpréteur du venv courant."""
    var.mkdir(parents=True, exist_ok=True)
    cible = var / "sbom.cdx.json"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "cyclonedx_py",
            "environment",
            "--output-format",
            "JSON",
            "--output-file",
            str(cible),
            sys.executable,
        ],
        check=True,
    )
    return cible
