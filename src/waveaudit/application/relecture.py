"""Persistance de l'état de relecture d'un lot (contrats §25 « Persistance », AD-19).

Seul écrivain de `var/sorties/<id_lot>/relecture.json`. Chaque écriture lit, modifie puis
remplace le fichier de façon atomique, sous un verrou propre au fichier. La lecture se passe de
verrou : le remplacement est atomique. Le module n'importe ni `lot.py` ni `moteur_demande.py` au
niveau module (`lot.py` l'importe).
"""

import json
import logging
import os
import threading
import time
from collections.abc import Callable, Collection, Iterable
from pathlib import Path
from typing import TYPE_CHECKING

from waveaudit.domaine.configuration import Configuration
from waveaudit.domaine.modeles import (
    CodeMotif,
    Fiche,
    Langue,
    Note,
    NoteInvalide,
    Rapport,
    ResultatElement,
    Statut,
)
from waveaudit.domaine.relecture import (
    EntreeRelecture,
    EtatRelecture,
    RefusRelecture,
    remplacer_fiche,
)

if TYPE_CHECKING:
    from waveaudit.application.moteur_demande import MoteurALaDemande, Occupation

_log = logging.getLogger(__name__)

FICHIER = "relecture.json"
FICHE_LOT = "lot.json"
FICHES_V010 = "fiches.json"
JOURNAL = "journal.jsonl"
# [revue A11/E14] os.replace retenté sur PermissionError (lecteur concurrent, antivirus).
ESSAIS_REMPLACEMENT = 10
PAUSE_REMPLACEMENT_S = 0.1
GENERATION_INTERROMPUE = "génération interrompue"
# [revue E2] Fiche de repli `repli_moteur` : la fiche courante est gardée.
MOTEUR_MUET = "Le moteur de génération ne répond pas ; la fiche n'a pas été régénérée."

_VERROU_GLOBAL = threading.Lock()
_VERROUS: dict[str, threading.Lock] = {}

Operation = Callable[[EntreeRelecture], EntreeRelecture]


def _verrou(dossier: Path) -> threading.Lock:
    cle = os.path.normcase(str((Path(dossier) / FICHIER).resolve()))
    with _VERROU_GLOBAL:
        return _VERROUS.setdefault(cle, threading.Lock())


def ecrire_atomique(chemin: Path, texte: str) -> None:
    """Écrit `texte` (UTF-8) dans `.<nom>.partiel`, puis `os.replace` vers `chemin`.

    `os.replace` est retenté `ESSAIS_REMPLACEMENT` fois à `PAUSE_REMPLACEMENT_S` d'écart sur
    `PermissionError` ; après le dernier essai, le provisoire est supprimé et l'erreur remonte.
    """
    provisoire = chemin.with_name(f".{chemin.name}.partiel")
    try:
        provisoire.write_text(texte, encoding="utf-8")
        for essai in range(1, ESSAIS_REMPLACEMENT + 1):
            try:
                os.replace(provisoire, chemin)
                return
            except PermissionError:
                if essai == ESSAIS_REMPLACEMENT:
                    raise
                time.sleep(PAUSE_REMPLACEMENT_S)
    finally:
        try:
            provisoire.unlink(missing_ok=True)
        except OSError:
            # Ne masque pas l'erreur d'origine ; le provisoire sera écrasé à la prochaine écriture.
            _log.warning("provisoire %s non supprimé", provisoire.name)


def _ecrire(dossier: Path, etat: EtatRelecture) -> None:
    ecrire_atomique(Path(dossier) / FICHIER, etat.model_dump_json(indent=2))


def _maj(e: EntreeRelecture, **champs: object) -> EntreeRelecture:
    """Copie revalidée (les invariants de `EntreeRelecture` sont vérifiés)."""
    return EntreeRelecture.model_validate(e.model_dump() | champs)


def _remplacer_entree(etat: EtatRelecture, entree: EntreeRelecture) -> EtatRelecture:
    entrees = [entree if e.index == entree.index else e for e in etat.entrees]
    return EtatRelecture.model_validate(etat.model_dump() | {"entrees": entrees})


def _trouver(etat: EtatRelecture, index: int) -> EntreeRelecture:
    for entree in etat.entrees:
        if entree.index == index:
            return entree
    raise RefusRelecture("entree_inconnue", "Cette entrée n'existe pas dans le lot.")


# --- Lecture ---------------------------------------------------------------------------------


def _occupee(occupation: "Occupation | None", id_lot: str, index: int) -> bool:
    return (
        occupation is not None
        and occupation.nature == "regeneration"
        and occupation.id_lot == id_lot
        and occupation.index == index
    )


def _presenter_entree(
    e: EntreeRelecture, id_lot: str, occupation: "Occupation | None"
) -> EntreeRelecture:
    """[revue A4/E5/E26] Génération interrompue, calculée en mémoire, sans écriture ni version."""
    if e.generation != "en_cours" or _occupee(occupation, id_lot, e.index):
        return e
    return e.model_copy(update={"generation": "echec", "erreur_generation": GENERATION_INTERROMPUE})


def _presenter(etat: EtatRelecture, occupation: "Occupation | None") -> EtatRelecture:
    if not any(e.generation == "en_cours" for e in etat.entrees):
        return etat
    entrees = [_presenter_entree(e, etat.id_lot, occupation) for e in etat.entrees]
    return etat.model_copy(update={"entrees": entrees})


def _lire_json(chemin: Path) -> dict | None:
    try:
        return json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _modele_du_journal(dossier: Path) -> str:
    try:
        lignes = (dossier / JOURNAL).read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    for ligne in lignes:
        try:
            evenement = json.loads(ligne)
        except ValueError:
            continue
        if evenement.get("type") == "lot_demarre":
            modele = (evenement.get("details") or {}).get("modele")
            return modele if isinstance(modele, str) else ""
    return ""


def _depuis_fiches_v010(dossier: Path, rapport: Rapport) -> EtatRelecture:
    """Lot v0.1.0 : état reconstruit en mémoire, trié par nom de note casefold (revue E9)."""
    brutes: list[tuple[str, dict]] = [
        (
            f.tracabilite.note,
            {
                "etat": "fiche",
                "candidats": f.tracabilite.candidats,
                "candidat_choisi": f.tracabilite.constat_id,
                "fiche_generee": f,
                "statut_relecture": "a_valider",
            },
        )
        for f in rapport.fiches
    ] + [
        (e.note, {"etat": "ecartee", "candidats": e.candidats, "ecartee": e})
        for e in rapport.ecartees
    ]
    brutes.sort(key=lambda b: (b[0].casefold(), b[0]))
    entrees = [
        EntreeRelecture.model_validate(
            {
                "index": index,
                "note": note,
                "source": None,
                "raison_invalide": None,
                "candidat_choisi": None,
                "fiche_generee": None,
                "fiche_corrigee": None,
                "ecartee": None,
                "statut_relecture": None,
            }
            | champs
        )
        for index, (note, champs) in enumerate(brutes, start=1)
    ]
    return EtatRelecture(
        id_lot=Path(dossier).name,
        langue="fr",
        modele=_modele_du_journal(Path(dossier)),
        modele_demande=None,
        entrees=entrees,
    )


def _charger_brut(dossier: Path) -> EtatRelecture:
    dossier = Path(dossier)
    chemin = dossier / FICHIER
    if chemin.is_file():
        return EtatRelecture.model_validate_json(chemin.read_text(encoding="utf-8"))
    fiches = dossier / FICHES_V010
    if fiches.is_file():
        rapport = Rapport.model_validate_json(fiches.read_text(encoding="utf-8"))
        return _depuis_fiches_v010(dossier, rapport)
    fiche_lot = _lire_json(dossier / FICHE_LOT)
    if isinstance(fiche_lot, dict) and fiche_lot.get("workflow") == "fiches":
        # [revue A12/E16] Lot pas encore initialisé (ou échoué avant) : état vide.
        return EtatRelecture(
            id_lot=dossier.name,
            langue=fiche_lot.get("langue") or "fr",
            modele="",
            modele_demande=fiche_lot.get("modele_demande"),
            entrees=[],
        )
    raise RefusRelecture("lot_inconnu", "Ce lot n'a pas d'état de relecture.")


def charger(dossier: Path, *, occupation: "Occupation | None" = None) -> EtatRelecture:
    """État de relecture du lot, sans aucune écriture (repli v0.1.0 et génération interrompue
    calculés en mémoire)."""
    return _presenter(_charger_brut(dossier), occupation)


# --- Écritures -------------------------------------------------------------------------------


def initialiser(
    dossier: Path,
    *,
    id_lot: str,
    langue: Langue,
    modele: str,
    modele_demande: str | None,
    elements: Iterable[Note | NoteInvalide],
) -> EtatRelecture:
    """Crée `relecture.json` : une entrée `attente` par élément, `index` 1..n."""
    entrees = [
        EntreeRelecture(
            index=index,
            note=element.fichier,
            source=element if isinstance(element, Note) else None,
            raison_invalide=element.raison if isinstance(element, NoteInvalide) else None,
            etat="attente",
            candidats=[],
            candidat_choisi=None,
            fiche_generee=None,
            fiche_corrigee=None,
            ecartee=None,
            statut_relecture=None,
        )
        for index, element in enumerate(elements, start=1)
    ]
    etat = EtatRelecture(
        id_lot=id_lot, langue=langue, modele=modele, modele_demande=modele_demande, entrees=entrees
    )
    with _verrou(dossier):
        _ecrire(dossier, etat)
    return etat


def enregistrer_resultat(dossier: Path, index: int, resultat: ResultatElement) -> EntreeRelecture:
    """Range le résultat du lot dans l'entrée `index` (`version + 1`, sans contrôle de version)."""
    with _verrou(dossier):
        etat = _charger_brut(dossier)
        entree = _trouver(etat, index)
        if isinstance(resultat, Fiche):
            champs: dict[str, object] = {
                "etat": "fiche",
                "candidats": resultat.tracabilite.candidats,
                "candidat_choisi": resultat.tracabilite.constat_id,
                "fiche_generee": resultat,
                "statut_relecture": "a_valider",
                "modele_generation": etat.modele or None,
                "ecartee": None,
            }
        else:
            champs = {
                "etat": "ecartee",
                "candidats": resultat.candidats,
                "ecartee": resultat,
                "candidat_choisi": None,
                "fiche_generee": None,
                "statut_relecture": None,
                "modele_generation": None,
            }
        # Le résultat remplace tout ce que l'entrée portait (correction et génération comprises).
        champs |= {"fiche_corrigee": None, "generation": "aucune", "erreur_generation": None}
        nouvelle = _maj(entree, **champs, version=entree.version + 1)
        _ecrire(dossier, _remplacer_entree(etat, nouvelle))
    return nouvelle


def _modifier_sous_verrou(
    dossier: Path,
    index: int,
    version_attendue: int | None,
    operation: Operation,
    occupation: "Occupation | None",
) -> EntreeRelecture:
    etat = _charger_brut(dossier)
    # Seule l'entrée visée est présentée : une autre entrée `en_cours` n'est jamais réécrite.
    entree = _presenter_entree(_trouver(etat, index), etat.id_lot, occupation)
    if version_attendue is not None and version_attendue != entree.version:
        raise RefusRelecture("conflit_version", "La fiche a été modifiée ailleurs.")
    nouvelle = operation(entree)
    if nouvelle == entree:
        # Interprétation du §25 (consigne de revue R1) : une règle sans effet renvoie l'entrée
        # telle quelle ; ni écriture ni incrément de version.
        return entree
    nouvelle = _maj(nouvelle, version=entree.version + 1)
    _ecrire(dossier, _remplacer_entree(etat, nouvelle))
    return nouvelle


def modifier(
    dossier: Path,
    index: int,
    version_attendue: int | None,
    operation: Operation,
    *,
    occupation: "Occupation | None" = None,
) -> EntreeRelecture:
    """Applique `operation` (règle pure du domaine) à l'entrée `index`, `version + 1`.

    `version_attendue` différente de la version lue → `RefusRelecture("conflit_version")` ;
    `None` : sans contrôle de version (régénération). La lecture sous verrou présente une
    génération interrompue (`occupation` : celle du processus, pour la reconnaître).
    """
    with _verrou(dossier):
        return _modifier_sous_verrou(dossier, index, version_attendue, operation, occupation)


def demarrer_regeneration(
    dossier: Path,
    index: int,
    version_attendue: int,
    constat_id: str,
    confirmer: bool,
    *,
    ids_catalogue: Collection[str] = (),
) -> EntreeRelecture:
    """Vérifie la demande de changement de candidat puis passe `generation="en_cours"`.

    Refus dans l'ordre du §25. `ids_catalogue` : identifiants du catalogue, seul contrôle
    d'existence d'un constat choisi pour une entrée `non_rattachee` (vide : refusé).

    [revue R2] Appelée sous le `VerrouUnique` déjà pris pour cette entrée (§26) : aucune
    régénération ne peut alors tourner dans ce processus, donc une entrée lue `en_cours` est
    toujours une génération interrompue, présentée `echec` et relançable. Pas de paramètre
    `occupation` (signature du §25) : passer l'occupation que l'appelant vient de prendre
    rendrait une entrée interrompue définitivement refusée (`generation_en_cours`). Une
    régénération en cours est refusée en amont par le verrou (409 `lot_en_cours`).
    """

    def verifier(e: EntreeRelecture) -> EntreeRelecture:
        # Ordre du §25 ; inatteignable sous le VerrouUnique (entrée `en_cours` présentée `echec`).
        if e.generation == "en_cours":
            raise RefusRelecture("generation_en_cours", "Une régénération est en cours.")
        non_rattachee = (
            e.etat == "ecartee"
            and e.ecartee is not None
            and e.ecartee.statut == Statut.NON_RATTACHEE
        )
        if e.etat == "attente" or (e.etat == "ecartee" and not non_rattachee):
            raise RefusRelecture("non_generable", "Cette entrée ne peut pas être générée.")
        if e.source is None:
            raise RefusRelecture(
                "source_absente", "La note source de cette entrée n'est pas enregistrée."
            )
        if constat_id == e.candidat_choisi:
            raise RefusRelecture("candidat_courant", "Ce constat est déjà celui de la fiche.")
        connus = set(ids_catalogue) if non_rattachee else {c.id for c in e.candidats}
        if constat_id not in connus:
            raise RefusRelecture(
                "candidat_inconnu", "Ce constat n'est pas proposé pour cette note."
            )
        if (e.fiche_corrigee is not None or e.statut_relecture == "validee") and not confirmer:
            raise RefusRelecture(
                "confirmation_requise", "Les corrections ou la validation seront perdues."
            )
        return _maj(e, generation="en_cours", erreur_generation=None)

    with _verrou(dossier):
        return _modifier_sous_verrou(dossier, index, version_attendue, verifier, None)


def _echec(message: str) -> Operation:
    def operation(e: EntreeRelecture) -> EntreeRelecture:
        return _maj(e, generation="echec", erreur_generation=message)

    return operation


def regenerer(
    config: Configuration,
    dossier: Path,
    index: int,
    constat_id: str,
    moteur: "MoteurALaDemande",
) -> None:
    """Régénère l'entrée `index` sur `constat_id`, dans le fil de travail, sous le
    `VerrouUnique` déjà pris (§24) ; libérer ce verrou reste au `finally` de l'appelant.

    Aucune exception ne sort : un échec est consigné dans l'entrée (`generation="echec"`).
    Aucun événement de lot, rien dans `journal.jsonl`.
    """
    from waveaudit.application.lot import config_pour_langue, sans_chemin
    from waveaudit.workflows.fiches import pipeline

    try:
        etat = _charger_brut(dossier)
        entree = _trouver(etat, index)
        if entree.source is None:
            raise RefusRelecture("source_absente", "La note source n'est pas enregistrée.")
        # [revue A15/A16] Modèle résolu du lot, pas la demande brute.
        modele = etat.modele_demande if config.moteur.mode == "externe" else etat.modele or None
        with moteur.utiliser(modele) as (ports, info):
            workflow = pipeline.creer(config_pour_langue(config, etat.langue), ports)
            fiche = workflow.rediger(entree.source, constat_id, entree.candidats)
            nom_modele = info.nom_modele
        if any(m.code == CodeMotif.REPLI_MOTEUR for m in fiche.motifs):
            operation = _echec(MOTEUR_MUET)
        else:

            def operation(e: EntreeRelecture) -> EntreeRelecture:
                return remplacer_fiche(e, fiche, constat_id, nom_modele)

        modifier(dossier, index, None, operation)
    except Exception as erreur:  # noqa: BLE001 - [revue E4] tout échec est consigné
        _log.exception("régénération de l'entrée %s en échec", index)
        message = getattr(erreur, "message", None) or str(erreur) or type(erreur).__name__
        try:
            modifier(dossier, index, None, _echec(sans_chemin(message)))
        except Exception:  # noqa: BLE001 - rien à qui remonter dans le fil de travail
            _log.exception("échec de régénération non consigné (entrée %s)", index)
