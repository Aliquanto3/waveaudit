"""Lecture des journaux Windows JSON et CSV (CAP-1, contrats §21 « Lecture »).

Les règles de correspondance et de normalisation des champs sont dans
`formats-incident.md` (« Champs normalisés »).
"""

import csv
import json
from datetime import datetime

from waveaudit.domaine.incident import Evenement, LigneIgnoree

_COLONNES_TETE = ("TimeCreated", "Id", "LogName", "ProviderName", "MachineName", "Message")
_COLONNES_REQUISES = ("TimeCreated", "Id", "MachineName")


def _normaliser_valeur(valeur: object) -> str | None:
    if valeur is None:
        return None
    if isinstance(valeur, bool):
        return "true" if valeur else "false"
    if isinstance(valeur, int):
        return str(valeur)
    if isinstance(valeur, (dict, list)):
        return json.dumps(valeur, ensure_ascii=False, sort_keys=True)
    if isinstance(valeur, str):
        return valeur if valeur.strip() else None
    return str(valeur)


def _normaliser_champs(donnees: dict) -> dict[str, str]:
    resultat: dict[str, str] = {}
    for cle, valeur in donnees.items():
        normalisee = _normaliser_valeur(valeur)
        if normalisee is not None:
            resultat[cle] = normalisee
    return resultat


def _horodatage_valide(valeur: object) -> datetime | None:
    if not isinstance(valeur, str):
        return None
    try:
        horodatage = datetime.fromisoformat(valeur)
    except ValueError:
        return None
    return horodatage if horodatage.tzinfo is not None else None


def lire_json(texte: str, fichier: str) -> tuple[list[Evenement], list[LigneIgnoree]]:
    """Lit un contenu JSON Windows (tableau d'objets) déjà décodé."""
    try:
        objets = json.loads(texte)
    except json.JSONDecodeError:
        return [], [LigneIgnoree(fichier=fichier, ligne=1, raison="JSON invalide")]
    if not isinstance(objets, list):
        return [], [LigneIgnoree(fichier=fichier, ligne=1, raison="racine JSON non tableau")]
    evenements: list[Evenement] = []
    ignorees: list[LigneIgnoree] = []
    for rang, objet in enumerate(objets, start=1):
        evenement = _evenement_json(objet, fichier, rang)
        if evenement is None:
            ignorees.append(LigneIgnoree(fichier=fichier, ligne=rang, raison="objet invalide"))
        else:
            evenements.append(evenement)
    return evenements, ignorees


def _evenement_json(objet: object, fichier: str, ligne: int) -> Evenement | None:
    if not isinstance(objet, dict):
        return None
    horodatage = _horodatage_valide(objet.get("TimeCreated"))
    if horodatage is None:
        return None
    id_evenement = objet.get("Id")
    if not isinstance(id_evenement, int) or isinstance(id_evenement, bool):
        return None
    hote = objet.get("MachineName")
    if not isinstance(hote, str) or not hote.strip():
        return None
    donnees = objet.get("Data", {})
    if not isinstance(donnees, dict):
        return None
    log_name = objet.get("LogName") or None
    message = objet.get("Message") or ""
    return Evenement(
        source="windows",
        fichier=fichier,
        ligne=ligne,
        horodatage=horodatage,
        hote=hote,
        event_id=id_evenement,
        log_name=log_name,
        programme=None,
        message=message,
        champs=_normaliser_champs(donnees),
    )


class _LignesPhysiques:
    r"""Itère sur les lignes physiques (terminées par `\n`) en les comptant.

    Le numéro de ligne ne dépend que des `\n` : un `\r` isolé ou doublé (`\r\r\n`) ne
    crée pas de ligne physique supplémentaire, contrairement à `csv.reader.line_num`.
    Un fichier sans aucun `\n` (fins de ligne `\r` seules) est découpé sur `\r`.
    """

    def __init__(self, texte: str) -> None:
        separateur = "\n" if "\n" in texte or "\r" not in texte else "\r"
        self._lignes = iter(texte.split(separateur))
        self.lues = 0

    def __iter__(self) -> "_LignesPhysiques":
        return self

    def __next__(self) -> str:
        ligne = next(self._lignes)
        self.lues += 1
        return ligne + "\n"


def lire_csv(texte: str, fichier: str) -> tuple[list[Evenement], list[LigneIgnoree]]:
    """Lit un contenu CSV Windows déjà décodé."""
    entete_brute = texte.splitlines()[0] if texte else ""
    separateur = ";" if entete_brute.count(";") > entete_brute.count(",") else ","
    lignes = _LignesPhysiques(texte)
    lecteur = csv.reader(lignes, delimiter=separateur)
    try:
        entete = next(lecteur)
    except (StopIteration, csv.Error):
        entete = None
    if entete is None or any(colonne not in entete for colonne in _COLONNES_REQUISES):
        return [], [LigneIgnoree(fichier=fichier, ligne=1, raison="en-tête CSV invalide")]
    evenements: list[Evenement] = []
    ignorees: list[LigneIgnoree] = []
    while True:
        debut = lignes.lues + 1
        try:
            ligne = next(lecteur)
        except StopIteration:
            break
        except csv.Error:
            ignorees.append(LigneIgnoree(fichier=fichier, ligne=debut, raison="CSV illisible"))
            continue
        if not ligne or all(valeur == "" for valeur in ligne):
            continue
        if len(ligne) != len(entete):
            ignorees.append(
                LigneIgnoree(fichier=fichier, ligne=debut, raison="colonnes incohérentes")
            )
            continue
        enregistrement = dict(zip(entete, ligne, strict=True))
        evenement = _evenement_csv(enregistrement, fichier, debut)
        if evenement is None:
            ignorees.append(
                LigneIgnoree(fichier=fichier, ligne=debut, raison="enregistrement invalide")
            )
        else:
            evenements.append(evenement)
    return evenements, ignorees


def _evenement_csv(enregistrement: dict, fichier: str, ligne: int) -> Evenement | None:
    horodatage = _horodatage_valide(enregistrement.get("TimeCreated"))
    if horodatage is None:
        return None
    id_brut = enregistrement.get("Id", "")
    if not (id_brut.isascii() and id_brut.isdecimal()):
        return None
    hote = enregistrement.get("MachineName", "")
    if not hote.strip():
        return None
    log_name = enregistrement.get("LogName") or None
    message = enregistrement.get("Message") or ""
    champs_bruts = {
        cle: valeur for cle, valeur in enregistrement.items() if cle not in _COLONNES_TETE
    }
    return Evenement(
        source="windows",
        fichier=fichier,
        ligne=ligne,
        horodatage=horodatage,
        hote=hote,
        event_id=int(id_brut),
        log_name=log_name,
        programme=None,
        message=message,
        champs=_normaliser_champs(champs_bruts),
    )
