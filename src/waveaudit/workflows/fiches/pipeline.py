"""Workflow `fiches` : note d'audit -> fiche de constat (contrats §5, AD-4, AD-6, AD-15)."""

from pathlib import Path

from waveaudit.domaine import cvss31, garde_fous
from waveaudit.domaine.configuration import Configuration
from waveaudit.domaine.erreurs import MoteurInjoignable, SortieInvalide
from waveaudit.domaine.modeles import (
    RUBRIQUES,
    Candidat,
    CodeMotif,
    ConstatType,
    EntreeEcartee,
    Fiche,
    Motif,
    Note,
    NoteInvalide,
    Rapport,
    ResultatElement,
    Statut,
    schema_sortie,
)
from waveaudit.domaine.ports import Message, Ports
from waveaudit.domaine.recherche import classer, requete_depuis_note
from waveaudit.workflows.fiches import prompt

NB_CANDIDATS = 3


class WorkflowFiches:
    """Reçoit ses ports et n'instancie rien (AD-15)."""

    def __init__(self, config: Configuration, ports: Ports) -> None:
        self._config = config
        self._ports = ports
        self._schema = schema_sortie(config.moteur.longueur_max_rubrique)
        # Lu une fois ici : `traiter` ne fait ensuite aucune lecture du catalogue sur disque.
        self._constats = ports.catalogue.constats()

    def preparer(self, dossier: Path) -> list[Note | NoteInvalide]:
        return self._ports.source_notes.lire(dossier)

    def traiter(self, element: Note | NoteInvalide) -> ResultatElement:
        if isinstance(element, NoteInvalide):
            return EntreeEcartee(
                note=element.fichier,
                statut=Statut.NON_TRAITEE,
                motif=Motif(code=CodeMotif.NOTE_INVALIDE, detail=element.raison),
                candidats=[],
                constat_attendu=None,
            )
        note = element
        recherche = self._config.recherche
        tous = classer(self._constats, requete_depuis_note(note), k1=recherche.k1, b=recherche.b)
        candidats = tous[:NB_CANDIDATS]
        if not candidats or candidats[0].score <= 0.0:
            return EntreeEcartee(
                note=note.fichier,
                statut=Statut.NON_RATTACHEE,
                motif=Motif(code=CodeMotif.AUCUN_CONSTAT, detail="score BM25 maximal nul"),
                candidats=candidats,
                constat_attendu=note.constat_attendu,
            )
        constat = self._ports.catalogue.obtenir(candidats[0].id)
        return self._rediger(note, constat, candidats)

    def assembler(self, resultats: list[ResultatElement]) -> Rapport:
        return Rapport(
            fiches=[r for r in resultats if isinstance(r, Fiche)],
            ecartees=[r for r in resultats if isinstance(r, EntreeEcartee)],
        )

    def _rediger(self, note: Note, constat: ConstatType, candidats: list[Candidat]) -> Fiche:
        moteur = self._config.moteur
        messages = prompt.construire(
            note, constat, self._ports.prefixe_systeme, moteur.taille_max_note
        )
        motifs: list[Motif] = []
        if prompt.tronquer(note.corps, moteur.taille_max_note)[1]:
            motifs.append(
                Motif(
                    code=CodeMotif.NOTE_TRONQUEE,
                    detail=f"corps tronqué à {moteur.taille_max_note} caractères",
                )
            )
        try:
            sortie = self._generer_avec_un_essai(messages)
        except SortieInvalide as erreur:
            sortie = _sortie_de_repli(constat)
            motifs.append(Motif(code=CodeMotif.REPLI_SORTIE_INVALIDE, detail=str(erreur)))
        except MoteurInjoignable as erreur:
            sortie = _sortie_de_repli(constat)
            motifs.append(Motif(code=CodeMotif.REPLI_MOTEUR, detail=str(erreur)))
        return garde_fous.appliquer(
            sortie,
            constat,
            note,
            candidats,
            moteur.longueur_max_rubrique,
            motifs_initiaux=motifs,
        )

    def _generer_avec_un_essai(self, messages: list[Message]) -> dict:
        """`SortieInvalide` : un seul nouvel essai ; `MoteurInjoignable` remonte aussitôt."""
        try:
            return self._generer(messages)
        except SortieInvalide:
            return self._generer(messages)

    def _generer(self, messages: list[Message]) -> dict:
        sortie = self._ports.moteur.generer_json(
            messages, self._schema, max_tokens=self._config.moteur.max_tokens
        )
        manquantes = [r for r in RUBRIQUES if not isinstance(sortie.get(r), str)]
        if manquantes:
            raise SortieInvalide(f"rubriques absentes : {', '.join(manquantes)}")
        return sortie


def _sortie_de_repli(constat: ConstatType) -> dict:
    """Sortie construite depuis le constat type, passée ensuite aux garde-fous."""
    metriques = cvss31.metriques_depuis_vecteur(constat.cvss_vecteur)
    return {
        "titre": constat.titre,
        "description": constat.description,
        "impact": constat.impact,
        "recommandation": constat.recommandation,
        "cvss": metriques.model_dump(),
    }


def creer(config: Configuration, ports: Ports) -> WorkflowFiches:
    """Fabrique enregistrée dans `workflows.registre.REGISTRE["fiches"]`."""
    return WorkflowFiches(config, ports)
