"""Adaptateur de lecture des notes brutes sur disque (CAP-1, contrats §14)."""

import logging
from pathlib import Path

import yaml
from pydantic import ValidationError

from waveaudit.domaine.erreurs import EntreeInvalide
from waveaudit.domaine.modeles import Note, NoteInvalide

_LOG = logging.getLogger(__name__)

_EXTENSIONS = (".md", ".txt")
_CHAMPS_CONNUS = frozenset({"titre", "actif", "severite_pressentie", "constat_attendu"})
_SEVERITES_VALIDES = frozenset({"critique", "elevee", "moyenne", "faible", "info"})


class _EnteteInvalide(Exception):
    """En-tête YAML illisible ou mal formé (interne : convertie en `NoteInvalide`)."""


class NotesFichiers:
    """Lit les notes brutes depuis un dossier (contrats §14).

    Implémente `domaine.ports.SourceNotes`.
    """

    def lire(self, dossier: Path) -> list[Note | NoteInvalide]:
        """Toutes les notes du dossier (`*.md`/`*.txt`, sans sous-dossiers), triées par nom.

        `EntreeInvalide` si le dossier est absent ou ne contient aucune note.
        """
        dossier = Path(dossier)
        if not dossier.is_dir():
            raise EntreeInvalide(f"notes : dossier introuvable ({dossier})")
        fichiers = sorted(
            (
                chemin
                for chemin in dossier.iterdir()
                if chemin.is_file() and chemin.suffix.lower() in _EXTENSIONS
            ),
            key=lambda chemin: chemin.name.casefold(),
        )
        if not fichiers:
            raise EntreeInvalide(f"notes : aucune note dans {dossier}")
        return [_lire_note(chemin) for chemin in fichiers]


def _lire_note(chemin: Path) -> Note | NoteInvalide:
    nom = chemin.name
    try:
        brut = chemin.read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError as erreur:
        return NoteInvalide(fichier=nom, raison=f"encodage invalide ({erreur})")
    texte = brut.replace("\r\n", "\n")
    try:
        champs, corps = _separer_entete(texte)
    except _EnteteInvalide as erreur:
        return NoteInvalide(fichier=nom, raison=str(erreur))
    titre, actif, severite, constat_attendu = _extraire_champs(champs, nom)
    try:
        return Note(
            fichier=nom,
            titre=titre,
            actif=actif,
            severite_pressentie=severite,
            constat_attendu=constat_attendu,
            corps=corps,
        )
    except ValidationError as erreur:
        return NoteInvalide(fichier=nom, raison=_resumer(erreur))


def _separer_entete(texte: str) -> tuple[dict, str]:
    """En-tête présent seulement si la première ligne vaut exactement `---`."""
    lignes = texte.split("\n")
    if not lignes or lignes[0] != "---":
        return {}, texte
    try:
        fin = lignes.index("---", 1)
    except ValueError:
        raise _EnteteInvalide("en-tête YAML non refermé") from None
    entete_texte = "\n".join(lignes[1:fin])
    corps = "\n".join(lignes[fin + 1 :])
    try:
        entete = yaml.safe_load(entete_texte) if entete_texte.strip() else {}
    except yaml.YAMLError as erreur:
        raise _EnteteInvalide(f"en-tête YAML illisible ({_resumer(erreur)})") from erreur
    if entete is None:
        entete = {}
    if not isinstance(entete, dict):
        raise _EnteteInvalide("en-tête YAML : doit être un mapping")
    return entete, corps


def _extraire_champs(
    champs: dict, nom: str
) -> tuple[str | None, str | None, str | None, str | None]:
    for cle in sorted(set(champs) - _CHAMPS_CONNUS):
        _LOG.warning("note %s : champ d'en-tête inconnu ignoré (%s)", nom, cle)

    def _texte(valeur: object) -> str | None:
        return None if valeur is None else str(valeur)

    titre = _texte(champs.get("titre"))
    actif = _texte(champs.get("actif"))
    constat_attendu = _texte(champs.get("constat_attendu"))

    severite = champs.get("severite_pressentie")
    if severite is not None and severite not in _SEVERITES_VALIDES:
        _LOG.warning("note %s : severite_pressentie hors liste ignorée (%r)", nom, severite)
        severite = None

    return titre, actif, severite, constat_attendu


def _resumer(erreur: Exception) -> str:
    """Message d'erreur sur une seule ligne."""
    if isinstance(erreur, ValidationError):
        return "; ".join(
            f"{'.'.join(str(x) for x in e['loc']) or 'racine'}: {e['msg']}" for e in erreur.errors()
        )
    return " ".join(str(erreur).split())
