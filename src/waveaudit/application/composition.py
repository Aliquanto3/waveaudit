"""Composition des ports (contrats §9, AD-2, AD-11). Seul module à instancier les adaptateurs.

`ouvrir` (fiches) et `ouvrir_moteur_incident` (CERT) sont les seuls points qui démarrent
llama-server, une fois par lot, par la fonction privée commune `_ouvrir_moteur`.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime

from waveaudit.adaptateurs import memoire_psutil
from waveaudit.adaptateurs.catalogue_yaml import CatalogueYaml
from waveaudit.adaptateurs.export_docx import ExportDocx
from waveaudit.adaptateurs.export_incident_docx import ExporteurIncidentDocx
from waveaudit.adaptateurs.journaux import SourceJournauxFichiers
from waveaudit.adaptateurs.llama_server import LlamaServer
from waveaudit.adaptateurs.moteur_openai import MoteurOpenAI
from waveaudit.adaptateurs.notes_fichiers import NotesFichiers
from waveaudit.adaptateurs.regles_yaml import CatalogueReglesYaml
from waveaudit.domaine.configuration import Configuration
from waveaudit.domaine.erreurs import ConfigurationInvalide
from waveaudit.domaine.ports import InfoMoteur, MesureMemoire, Moteur, Ports, PortsIncident
from waveaudit.installation import manifeste
from waveaudit.installation.manifeste import Artefact

ROLES_MODELE = ("modele_defaut", "modele_repli", "candidat")
OCTETS_PAR_GO = 1024**3


def creer_mesure_memoire() -> MesureMemoire:
    """Seul accès du banc à la mesure mémoire."""
    return memoire_psutil.MesureMemoirePsutil()


def choisir_modele(
    config: Configuration, artefacts: list[Artefact], modele: str | None
) -> Artefact:
    """`modele`, sinon `config.moteur.modele`, sinon défaut, ou repli si la RAM est trop basse."""
    nom = modele or config.moteur.modele
    if nom:
        artefact = manifeste.par_nom(artefacts, nom)
        if artefact.role not in ROLES_MODELE:
            raise ConfigurationInvalide(f"{nom} n'est pas un modèle (rôle {artefact.role})")
        return artefact
    seuil = config.moteur.ram_min_defaut_go * OCTETS_PAR_GO
    if memoire_psutil.ram_disponible_octets() < seuil:
        return manifeste.par_role(artefacts, "modele_repli")
    return manifeste.par_role(artefacts, "modele_defaut")


def _moteur(
    config: Configuration, base_url: str, modele_api: str, artefact: Artefact | None = None
) -> MoteurOpenAI:
    """`artefact` (local-gere) : son `mode_json` et son `repeat_penalty` priment sur la
    configuration (§22, §3, §11)."""
    m = config.moteur
    repeat_penalty = artefact.repeat_penalty if artefact else None
    if repeat_penalty is None:
        repeat_penalty = m.repeat_penalty
    return MoteurOpenAI(
        base_url,
        modele_api,
        cle_api=m.cle_api,
        timeout_s=m.timeout_s,
        temperature=m.temperature,
        seed=m.seed,
        repeat_penalty=repeat_penalty,
        mode_json=(artefact.mode_json if artefact else None) or m.mode_json,
        reflexion=artefact.reflexion if artefact else None,
    )


def _ports(
    config: Configuration, moteur: MoteurOpenAI, exporteur: ExportDocx, prefixe_systeme: str
) -> Ports:
    return Ports(
        moteur=moteur,
        catalogue=CatalogueYaml(config.chemins.catalogue),
        source_notes=NotesFichiers(),
        exporteur=exporteur,
        prefixe_systeme=prefixe_systeme,
    )


@contextmanager
def _ouvrir_moteur(
    config: Configuration, modele: str | None, id_lot: str | None
) -> Iterator[tuple[MoteurOpenAI, str, InfoMoteur]]:
    """Résolution et cycle de vie du moteur, communs à `ouvrir` et `ouvrir_moteur_incident`."""
    m = config.moteur
    if m.mode == "externe":
        if not m.base_url:
            raise ConfigurationInvalide("moteur.base_url est vide en mode externe")
        modele_api = modele or m.modele_api
        moteur = _moteur(config, m.base_url, modele_api)
        try:
            yield (
                moteur,
                m.prefixe_systeme,
                InfoMoteur(nom_modele=modele_api or "externe", pid=None, base_url=m.base_url),
            )
        finally:
            moteur.fermer()
        return

    var = config.chemins.var
    artefacts = manifeste.charger(config.chemins.manifeste)
    artefact = choisir_modele(config, artefacts, modele)
    binaire = manifeste.chemin(manifeste.par_role(artefacts, "moteur"), var)
    gguf = manifeste.chemin(artefact, var)
    for fichier in (binaire, gguf):
        if not fichier.is_file():
            raise ConfigurationInvalide(f"{fichier} absent : lancer `waveaudit installer`")
    suffixe = id_lot or datetime.now().strftime("%Y%m%d-%H%M%S")
    journal = var / "journaux" / f"llama-server-{suffixe}.log"
    serveur = LlamaServer(binaire, gguf, m.ctx, m.threads, m.delai_demarrage_s, journal)
    with serveur:
        moteur = _moteur(config, serveur.base_url, m.modele_api or artefact.nom, artefact)
        try:
            yield (
                moteur,
                artefact.prefixe_systeme,
                InfoMoteur(nom_modele=artefact.nom, pid=serveur.pid, base_url=serveur.base_url),
            )
        finally:
            moteur.fermer()


@contextmanager
def ouvrir(
    config: Configuration, modele: str | None, *, id_lot: str | None = None
) -> Iterator[tuple[Ports, InfoMoteur]]:
    """Ports et moteur d'un lot. `id_lot` nomme le journal `llama-server-<id_lot>.log`."""
    # Le thème privé est validé ici (ExportDocx), avant tout démarrage du moteur.
    exporteur = ExportDocx(config.chemins.theme_prive)
    with _ouvrir_moteur(config, modele, id_lot) as (moteur, prefixe_systeme, info):
        yield _ports(config, moteur, exporteur, prefixe_systeme), info


@contextmanager
def ouvrir_moteur_incident(
    config: Configuration, modele: str | None, *, id_lot: str | None = None
) -> Iterator[tuple[Moteur, str, InfoMoteur]]:
    """(moteur, prefixe_systeme, info) du workflow incident ; même cycle de vie qu'`ouvrir`.

    Aucun port des fiches (catalogue, notes, exporteur Word) n'est instancié.
    """
    with _ouvrir_moteur(config, modele, id_lot) as ouvert:
        yield ouvert


def creer_ports_incident(config: Configuration) -> PortsIncident:
    """Ports du workflow incident, sans processus ni connexion (contrats §21, AD-17).

    Le catalogue de règles et le thème privé sont validés ici (`ConfigurationInvalide`), avant
    toute lecture de journaux et toute ouverture du moteur.
    """
    return PortsIncident(
        source_journaux=SourceJournauxFichiers(config.incident.decalage_syslog),
        regles=CatalogueReglesYaml(config.chemins.regles),
        exporteur=ExporteurIncidentDocx(
            config.chemins.theme_prive, max_preuves=config.incident.max_preuves
        ),
    )
