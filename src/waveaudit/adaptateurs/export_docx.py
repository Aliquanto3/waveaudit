"""Adaptateur d'export Word (CAP-6, CAP-8, CAP-13, contrats §17 et §27 [v2], AD-14).

Implémente `domaine.ports.Exporteur`. Le rapport d'incident (CERT, contrats §21) réutilise
`BANDEAU` sans modifier ce module.
"""

import os
import re
import uuid
from collections.abc import Callable
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.table import Table

from waveaudit.adaptateurs.theme_generique import (
    COULEUR_PRIMAIRE_DEFAUT,
    COULEUR_SECONDAIRE_DEFAUT,
    appliquer_couleurs,
    assurer_styles_titre,
    charger_theme,
    document_generique,
)
from waveaudit.domaine.erreurs import ConfigurationInvalide
from waveaudit.domaine.modeles import (
    CodeMotif,
    EntreeEcartee,
    Fiche,
    Langue,
    Motif,
    Rapport,
    Statut,
)
from waveaudit.domaine.ports import OptionsExport

BANDEAU = "Démonstration — données fictives"

# [v2] Libellés par langue (contrats §27, formats.md « Libellés Word par langue »). Les valeurs
# françaises restent celles de contrats §17, inchangées depuis la v0.1.0.
LIBELLES: dict[Langue, dict[str, object]] = {
    "fr": {
        "titre": "Rapport de constats",
        "synthese": ("N°", "Titre", "Sévérité", "Score", "Statut"),
        "description": "Description",
        "impact": "Impact",
        "recommandation": "Recommandation",
        "cvss": "CVSS 3.1",
        "references": "Références",
        "statut": "Statut",
        "tracabilite": "Traçabilité",
        "severites": {
            "aucune": "Aucune",
            "faible": "Faible",
            "moyenne": "Moyenne",
            "elevee": "Élevée",
            "critique": "Critique",
        },
        "ok": "OK",
        "a_revoir": "À revoir",
        "annexe_titre": "Annexe — notes écartées",
        "annexe_entetes": ("Note", "Statut", "Motif"),
        "marque": "Non validée",
        "validee": "Validée",
        "motif_non_validee": "fiche non validée, exclue du rapport final",
        # Mots inline des rubriques CVSS et Traçabilité (contrats §17), hors table §27.
        "vecteur": "Vecteur",
        "score": "Score",
        "severite": "Sévérité",
        "note": "Note",
        "constat_type": "Constat type",
    },
    "en": {
        "titre": "Findings report",
        "synthese": ("No.", "Title", "Severity", "Score", "Status"),
        "description": "Description",
        "impact": "Impact",
        "recommandation": "Recommendation",
        "cvss": "CVSS 3.1",
        "references": "References",
        "statut": "Status",
        "tracabilite": "Traceability",
        "severites": {
            "aucune": "None",
            "faible": "Low",
            "moyenne": "Medium",
            "elevee": "High",
            "critique": "Critical",
        },
        "ok": "OK",
        "a_revoir": "To review",
        "annexe_titre": "Appendix — excluded notes",
        "annexe_entetes": ("Note", "Status", "Reason"),
        "marque": "Not validated",
        "validee": "Validated",
        "motif_non_validee": "not validated, excluded from the final report",
        "vecteur": "Vector",
        "score": "Score",
        "severite": "Severity",
        "note": "Note",
        "constat_type": "Finding template",
    },
}

# [LIB] Word `en` : libellés des statuts d'entrée écartée et des codes de motif, pour qu'aucun
# code brut ni texte français n'atteigne le lecteur. Le Word `fr` garde le rendu v0.1.0
# (statut brut, `code : detail`, contrats §17 et §27) : ces tables ne servent qu'en `en`.
STATUTS_ECARTES_EN: dict[Statut, str] = {
    Statut.NON_TRAITEE: "Not processed",
    Statut.NON_RATTACHEE: "Not matched",
}
MOTIFS_EN: dict[CodeMotif, str] = {
    CodeMotif.REFERENCE_RETIREE: "Reference removed",
    CodeMotif.VECTEUR_INVALIDE: "Invalid CVSS vector",
    CodeMotif.RUBRIQUE_COMPLETEE: "Section completed",
    CodeMotif.NOTE_TRONQUEE: "Note truncated",
    CodeMotif.REPLI_SORTIE_INVALIDE: "Fallback — invalid output",
    CodeMotif.REPLI_MOTEUR: "Engine fallback",
    CodeMotif.NOTE_INVALIDE: "Invalid note",
    CodeMotif.AUCUN_CONSTAT: "No matching finding",
    CodeMotif.INDICATEUR_RETIRE: "Indicator removed",
    CodeMotif.REPETITION: "Repetitive section",
    CodeMotif.LANGUE: "Language mismatch",
    CodeMotif.LOT_INTERROMPU: "Batch interrupted",
}
RUBRIQUES_EN: dict[str, str] = {
    "titre": "Title",
    "description": "Description",
    "impact": "Impact",
    "recommandation": "Recommendation",
}
# Suffixes de `qualite_texte.motif_langue` (contrats §6 étape 6), après « <rubrique> : ».
_SUFFIXE_LANGUE_NON_LATIN = "écriture non latine"
_SUFFIXE_LANGUE_MOTS_OUTILS = re.compile(r"mots-outils (fr|en)")
# Détail émis par `workflows/fiches/pipeline.py` pour une note tronquée.
_DETAIL_NOTE_TRONQUEE = re.compile(r"corps tronqué à (\d+) caractères")


def _detail_brut(detail: str) -> str | None:
    """Jeton, indicateur ou vecteur CVSS : une valeur, lisible dans toutes les langues."""
    return detail


def _detail_omis(detail: str) -> str | None:
    """Phrase française (erreur moteur, raison d'invalidité, seuil) ou détail redondant."""
    return None


def _detail_rubrique(detail: str) -> str | None:
    return RUBRIQUES_EN.get(detail)


def _detail_langue(detail: str) -> str | None:
    nom, _, suffixe = detail.partition(" : ")
    rubrique = RUBRIQUES_EN.get(nom)
    if rubrique is None:
        return None
    if suffixe == _SUFFIXE_LANGUE_NON_LATIN:
        return f"{rubrique}, non-Latin script"
    trouve = _SUFFIXE_LANGUE_MOTS_OUTILS.fullmatch(suffixe)
    if trouve is not None:
        return f"{rubrique}, {trouve.group(1)} function words"
    return rubrique


def _detail_note_tronquee(detail: str) -> str | None:
    trouve = _DETAIL_NOTE_TRONQUEE.fullmatch(detail)
    return f"cut at {trouve.group(1)} characters" if trouve is not None else None


# Chaque code est classé ici explicitement (test de complétude) : rendu anglais du `detail`,
# `None` pour l'omettre. Un format de `detail` non reconnu est omis, jamais recopié.
DETAILS_EN: dict[CodeMotif, Callable[[str], str | None]] = {
    CodeMotif.REFERENCE_RETIREE: _detail_brut,
    CodeMotif.VECTEUR_INVALIDE: _detail_brut,
    CodeMotif.INDICATEUR_RETIRE: _detail_brut,
    CodeMotif.RUBRIQUE_COMPLETEE: _detail_rubrique,
    CodeMotif.REPETITION: _detail_rubrique,
    CodeMotif.LANGUE: _detail_langue,
    CodeMotif.NOTE_TRONQUEE: _detail_note_tronquee,
    CodeMotif.REPLI_SORTIE_INVALIDE: _detail_omis,
    CodeMotif.REPLI_MOTEUR: _detail_omis,
    CodeMotif.NOTE_INVALIDE: _detail_omis,
    CodeMotif.AUCUN_CONSTAT: _detail_omis,
    CodeMotif.LOT_INTERROMPU: _detail_omis,
}

# [v2] `BANDEAU` reste la constante publique française (contrats §17).
BANDEAUX: dict[Langue, str] = {"fr": BANDEAU, "en": "Demonstration — fictitious data"}

# Caractères interdits en XML 1.0 : python-docx lève ValueError s'il en reçoit un.
_HORS_XML = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff￾￿]")


class ExportDocx:
    """Exporte un `Rapport` en `.docx` (contrats §17, §27). Thème privé s'il est fourni."""

    def __init__(self, theme_prive: Path) -> None:
        """Valide le thème privé dès la composition : `ConfigurationInvalide` avant le lot."""
        self._theme_prive = Path(theme_prive)
        self._theme = charger_theme(self._theme_prive)
        self._modele = self._theme_prive / "modele.docx"
        if self._modele.is_file():
            self._ouvrir_modele()

    def exporter(
        self,
        rapport: Rapport,
        chemin: Path,
        options: OptionsExport = OptionsExport(),  # noqa: B008 - dataclass figée, immuable
    ) -> None:
        libelles = LIBELLES[options.langue]
        document = self._document_de_depart(self._theme)

        _bandeau_en_tete_pied(document, BANDEAUX[options.langue])
        document.add_heading(str(libelles["titre"]), level=0)
        _table_synthese(document, rapport.fiches, libelles, options)
        for index, fiche in enumerate(rapport.fiches, start=1):
            _section_fiche(document, index, fiche, libelles, options)
        if rapport.ecartees or (options.mode == "final" and options.non_validees):
            _annexe(document, rapport.ecartees, options, libelles)

        chemin = Path(chemin)
        chemin.parent.mkdir(parents=True, exist_ok=True)
        # [revue E19] Provisoire unique : deux exports simultanés (service, contrats §27) ne se
        # mélangent pas même si un verrou amont venait à manquer.
        provisoire = chemin.with_name(f".{chemin.name}.{uuid.uuid4().hex}.partiel")
        try:
            document.save(str(provisoire))
            os.replace(provisoire, chemin)
        finally:
            provisoire.unlink(missing_ok=True)

    def _ouvrir_modele(self) -> Document:
        try:
            return Document(str(self._modele))
        except Exception as erreur:  # zip corrompu, pas un .docx : python-docx lève divers types
            raise ConfigurationInvalide(
                f"modele.docx du thème privé illisible : {erreur}"
            ) from erreur

    def _document_de_depart(self, theme: dict) -> Document:
        if self._modele.is_file():
            document = self._ouvrir_modele()
            assurer_styles_titre(document)
        else:
            document = document_generique()
        couleur_primaire = theme.get("couleur_primaire")
        couleur_secondaire = theme.get("couleur_secondaire")
        if couleur_primaire or couleur_secondaire:
            appliquer_couleurs(
                document,
                str(couleur_primaire or COULEUR_PRIMAIRE_DEFAUT),
                str(couleur_secondaire or COULEUR_SECONDAIRE_DEFAUT),
            )
        return document


def _propre(texte: str) -> str:
    """Retire les caractères interdits en XML (un NUL venu du modèle ferait échouer l'export)."""
    return _HORS_XML.sub("", texte)


def _paragraphe(document: Document, texte: str) -> None:
    document.add_paragraph(_propre(texte))


def _conteneurs_bandeau(section, pages_paires: bool):
    yield section.header
    yield section.footer
    if section.different_first_page_header_footer:
        yield section.first_page_header
        yield section.first_page_footer
    if pages_paires:
        yield section.even_page_header
        yield section.even_page_footer


def _bandeau_en_tete_pied(document: Document, bandeau: str = BANDEAU) -> None:
    """Bandeau dans chaque en-tête et pied, sans effacer le contenu d'un modèle (logo, mentions).

    Un en-tête lié au précédent partage sa définition : le test `bandeau in …` évite le doublon.
    """
    pages_paires = document.settings.odd_and_even_pages_header_footer
    for section in document.sections:
        for conteneur in _conteneurs_bandeau(section, pages_paires):
            paragraphes = conteneur.paragraphs
            if any(p.text == bandeau for p in paragraphes):
                continue
            vide = paragraphes and not paragraphes[0].text and not paragraphes[0].runs
            paragraphe = paragraphes[0] if vide else conteneur.add_paragraph()
            paragraphe.text = bandeau
            paragraphe.alignment = WD_ALIGN_PARAGRAPH.CENTER


def _style_table(document: Document, style_prefere: str) -> str | None:
    """`style_prefere` s'il existe (modèle privé), sinon `Table Grid`, sinon le style par défaut."""
    noms = {s.name for s in document.styles}
    for nom in (style_prefere, "Table Grid"):
        if nom in noms:
            return nom
    return None


def _motif_affiche(motif: Motif, langue: Langue) -> str:
    """[LIB] `fr` : `code : detail` (v0.1.0, contrats §17). `en` : libellé, puis le détail
    rendu en anglais quand son format est connu (`DETAILS_EN`), sinon le libellé seul."""
    if langue == "fr":
        return f"{motif.code} : {motif.detail}"
    libelle = MOTIFS_EN[motif.code]
    detail = DETAILS_EN[motif.code](motif.detail)
    return libelle if detail is None else f"{libelle} : {detail}"


def _statut_ecartee_affiche(statut: Statut, langue: Langue) -> str:
    """[LIB] `fr` : statut brut (v0.1.0) ; `en` : libellé anglais."""
    return str(statut) if langue == "fr" else STATUTS_ECARTES_EN[statut]


def _statut_affiche(fiche: Fiche, libelles: dict, options: OptionsExport) -> str:
    """[v2] En mode final, « Validée », sans égard au statut de génération (contrats §27)."""
    if options.mode == "final":
        return str(libelles["validee"])
    return str(libelles["ok"]) if fiche.statut == "ok" else str(libelles["a_revoir"])


def _table_synthese(
    document: Document, fiches: list[Fiche], libelles: dict, options: OptionsExport
) -> Table:
    table = document.add_table(rows=1, cols=5)
    table.style = _style_table(document, "Light Grid Accent 1")
    entetes = table.rows[0].cells
    for cellule, texte in zip(entetes, libelles["synthese"], strict=True):
        cellule.text = texte
    severites = libelles["severites"]
    for index, fiche in enumerate(fiches, start=1):
        cellules = table.add_row().cells
        valeurs = (
            str(index),
            fiche.titre,
            severites[fiche.cvss.severite],
            f"{fiche.cvss.score:.1f}",
            _statut_affiche(fiche, libelles, options),
        )
        for cellule, texte in zip(cellules, valeurs, strict=True):
            cellule.text = _propre(texte)
    return table


def _marque_titre(fiche: Fiche, libelles: dict, options: OptionsExport) -> str:
    """[v2] « — Non validée » dans le titre, en brouillon seulement (contrats §27)."""
    if options.mode == "brouillon" and fiche.tracabilite.note in options.non_validees:
        return f" — {libelles['marque']}"
    return ""


def _section_fiche(
    document: Document, index: int, fiche: Fiche, libelles: dict, options: OptionsExport
) -> None:
    marque = _marque_titre(fiche, libelles, options)
    document.add_heading(_propre(f"{index}. {fiche.titre}{marque}"), level=2)

    document.add_heading(str(libelles["description"]), level=3)
    _paragraphe(document, fiche.description)

    document.add_heading(str(libelles["impact"]), level=3)
    _paragraphe(document, fiche.impact)

    document.add_heading(str(libelles["recommandation"]), level=3)
    _paragraphe(document, fiche.recommandation)

    document.add_heading(str(libelles["cvss"]), level=3)
    severites = libelles["severites"]
    _paragraphe(
        document,
        f"{libelles['vecteur']} : {fiche.cvss.vecteur} — "
        f"{libelles['score']} : {fiche.cvss.score:.1f} — "
        f"{libelles['severite']} : {severites[fiche.cvss.severite]}",
    )

    document.add_heading(str(libelles["references"]), level=3)
    for reference in fiche.references:
        _paragraphe(document, f"{reference.id} — {reference.titre} — {reference.url}")

    document.add_heading(str(libelles["statut"]), level=3)
    if options.mode == "final":
        document.add_paragraph(str(libelles["validee"]))
    elif fiche.statut == "ok":
        document.add_paragraph(str(libelles["ok"]))
    else:
        document.add_paragraph(str(libelles["a_revoir"]))
        for motif in fiche.motifs:
            _paragraphe(document, _motif_affiche(motif, options.langue))

    document.add_heading(str(libelles["tracabilite"]), level=3)
    _paragraphe(
        document,
        f"{libelles['note']} : {fiche.tracabilite.note} — "
        f"{libelles['constat_type']} : {fiche.tracabilite.constat_id}",
    )


def _annexe(
    document: Document, ecartees: list[EntreeEcartee], options: OptionsExport, libelles: dict
) -> None:
    document.add_heading(str(libelles["annexe_titre"]), level=1)
    table = document.add_table(rows=1, cols=3)
    table.style = _style_table(document, "Table Grid")
    entetes = table.rows[0].cells
    for cellule, texte in zip(entetes, libelles["annexe_entetes"], strict=True):
        cellule.text = texte
    for entree in ecartees:
        cellules = table.add_row().cells
        valeurs = (
            entree.note,
            _statut_ecartee_affiche(entree.statut, options.langue),
            _motif_affiche(entree.motif, options.langue),
        )
        for cellule, texte in zip(cellules, valeurs, strict=True):
            cellule.text = _propre(texte)
    if options.mode == "final":
        # [revue A17] Les fiches non validées sont listées en annexe, jamais dans le corps.
        for note in sorted(options.non_validees, key=str.casefold):
            cellules = table.add_row().cells
            valeurs = (note, str(libelles["marque"]), str(libelles["motif_non_validee"]))
            for cellule, texte in zip(cellules, valeurs, strict=True):
                cellule.text = _propre(texte)
