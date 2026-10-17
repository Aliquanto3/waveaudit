"""Téléchargement vérifié des artefacts (contrats §11, AD-12). Seul module à faire ces appels.

`httpx.Client(trust_env=True, ...)` est autorisé ici seulement, pour laisser passer le proxy
d'entreprise éventuel lors de l'installation (contrats §11).
"""

import hashlib
import zipfile
from pathlib import Path

import httpx

from waveaudit.domaine.erreurs import EmpreinteInvalide
from waveaudit.installation.manifeste import Artefact, chemin, par_role


def _sha256(fichier: Path) -> str:
    hachage = hashlib.sha256()
    with fichier.open("rb") as flux:
        for bloc in iter(lambda: flux.read(1024 * 1024), b""):
            hachage.update(bloc)
    return hachage.hexdigest()


def _empreinte_valide(fichier: Path, artefact: Artefact) -> bool:
    return (
        fichier.is_file()
        and fichier.stat().st_size == artefact.taille
        and _sha256(fichier) == artefact.sha256
    )


def _telecharger_vers(url: str, cible: Path, transport: httpx.BaseTransport | None) -> None:
    """Télécharge `url` vers `<cible>.part`, puis renomme en `cible`."""
    cible.parent.mkdir(parents=True, exist_ok=True)
    partiel = cible.with_name(cible.name + ".part")
    with httpx.Client(transport=transport, trust_env=True, timeout=None) as client:
        with client.stream("GET", url) as reponse:
            reponse.raise_for_status()
            with partiel.open("wb") as flux:
                for bloc in reponse.iter_bytes():
                    flux.write(bloc)
    partiel.replace(cible)


def telecharger(
    artefact: Artefact, var: Path, transport: httpx.BaseTransport | None = None
) -> Path:
    """Télécharge, vérifie et (si besoin) extrait l'artefact. Retourne son chemin final.

    Un fichier déjà présent avec la bonne empreinte est sauté. Avec une mauvaise empreinte (ou
    absent), il est (re)téléchargé une fois ; un nouvel écart lève `EmpreinteInvalide` après
    suppression du fichier.
    """
    fichier = var / f"{artefact.nom}.zip" if artefact.extraire else var / artefact.destination
    if not _empreinte_valide(fichier, artefact):
        if fichier.is_file():
            fichier.unlink()
        _telecharger_vers(artefact.url, fichier, transport)
        if not _empreinte_valide(fichier, artefact):
            fichier.unlink(missing_ok=True)
            raise EmpreinteInvalide(f"empreinte invalide pour {artefact.nom} ({fichier})")
    if artefact.extraire:
        destination = var / artefact.destination
        with zipfile.ZipFile(fichier) as archive:
            archive.extractall(destination)
    return chemin(artefact, var)


def installer(
    manifeste: list[Artefact],
    var: Path,
    candidats: bool,
    transport: httpx.BaseTransport | None = None,
) -> list[Path]:
    """Installe le moteur, le modèle par défaut et le modèle de repli ; `candidats` ajoute les
    artefacts de rôle `candidat`."""
    roles = ["moteur", "modele_defaut", "modele_repli"]
    artefacts = [par_role(manifeste, role) for role in roles]
    if candidats:
        artefacts += [artefact for artefact in manifeste if artefact.role == "candidat"]
    return [telecharger(artefact, var, transport) for artefact in artefacts]
