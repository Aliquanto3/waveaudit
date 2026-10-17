"""Adaptateur d'export Word (CAP-6, contrats §17, AD-14). Implémente `domaine.ports.Exporteur`.

Le rapport d'incident (CERT, contrats §21) réutilise `BANDEAU` sans modifier ce module.
"""

import os
import re
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
from waveaudit.domaine.modeles import EntreeEcartee, Fiche, Rapport

BANDEAU = "Démonstration — données fictives"

# Caractères interdits en XML 1.0 : python-docx lève ValueError s'il en reçoit un.
_HORS_XML = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff￾￿]")

_SEVERITES_AFFICHEES: dict[str, str] = {
    "aucune": "Aucune",
    "faible": "Faible",
    "moyenne": "Moyenne",
    "elevee": "Élevée",
    "critique": "Critique",
}


class ExportDocx:
    """Exporte un `Rapport` en `.docx` (contrats §17). Thème privé si `theme_prive` le fournit."""

    def __init__(self, theme_prive: Path) -> None:
        """Valide le thème privé dès la composition : `ConfigurationInvalide` avant le lot."""
        self._theme_prive = Path(theme_prive)
        self._theme = charger_theme(self._theme_prive)
        self._modele = self._theme_prive / "modele.docx"
        if self._modele.is_file():
            self._ouvrir_modele()

    def exporter(self, rapport: Rapport, chemin: Path) -> None:
        document = self._document_de_depart(self._theme)

        _bandeau_en_tete_pied(document)
        document.add_heading("Rapport de constats", level=0)
        _table_synthese(document, rapport.fiches)
        for index, fiche in enumerate(rapport.fiches, start=1):
            _section_fiche(document, index, fiche)
        if rapport.ecartees:
            _annexe_ecartees(document, rapport.ecartees)

        chemin = Path(chemin)
        chemin.parent.mkdir(parents=True, exist_ok=True)
        provisoire = chemin.with_name(f".{chemin.name}.partiel")
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


def _bandeau_en_tete_pied(document: Document) -> None:
    """Bandeau dans chaque en-tête et pied, sans effacer le contenu d'un modèle (logo, mentions).

    Un en-tête lié au précédent partage sa définition : le test `BANDEAU in …` évite le doublon.
    """
    pages_paires = document.settings.odd_and_even_pages_header_footer
    for section in document.sections:
        for conteneur in _conteneurs_bandeau(section, pages_paires):
            paragraphes = conteneur.paragraphs
            if any(p.text == BANDEAU for p in paragraphes):
                continue
            vide = paragraphes and not paragraphes[0].text and not paragraphes[0].runs
            paragraphe = paragraphes[0] if vide else conteneur.add_paragraph()
            paragraphe.text = BANDEAU
            paragraphe.alignment = WD_ALIGN_PARAGRAPH.CENTER


def _style_table(document: Document, style_prefere: str) -> str | None:
    """`style_prefere` s'il existe (modèle privé), sinon `Table Grid`, sinon le style par défaut."""
    noms = {s.name for s in document.styles}
    for nom in (style_prefere, "Table Grid"):
        if nom in noms:
            return nom
    return None


def _table_synthese(document: Document, fiches: list[Fiche]) -> Table:
    table = document.add_table(rows=1, cols=5)
    table.style = _style_table(document, "Light Grid Accent 1")
    entetes = table.rows[0].cells
    for cellule, texte in zip(entetes, ("N°", "Titre", "Sévérité", "Score", "Statut"), strict=True):
        cellule.text = texte
    for index, fiche in enumerate(fiches, start=1):
        cellules = table.add_row().cells
        valeurs = (
            str(index),
            fiche.titre,
            _SEVERITES_AFFICHEES[fiche.cvss.severite],
            f"{fiche.cvss.score:.1f}",
            "OK" if fiche.statut == "ok" else "À revoir",
        )
        for cellule, texte in zip(cellules, valeurs, strict=True):
            cellule.text = _propre(texte)
    return table


def _section_fiche(document: Document, index: int, fiche: Fiche) -> None:
    document.add_heading(_propre(f"{index}. {fiche.titre}"), level=2)

    document.add_heading("Description", level=3)
    _paragraphe(document, fiche.description)

    document.add_heading("Impact", level=3)
    _paragraphe(document, fiche.impact)

    document.add_heading("Recommandation", level=3)
    _paragraphe(document, fiche.recommandation)

    document.add_heading("CVSS 3.1", level=3)
    _paragraphe(
        document,
        f"Vecteur : {fiche.cvss.vecteur} — Score : {fiche.cvss.score:.1f} — "
        f"Sévérité : {_SEVERITES_AFFICHEES[fiche.cvss.severite]}",
    )

    document.add_heading("Références", level=3)
    for reference in fiche.references:
        _paragraphe(document, f"{reference.id} — {reference.titre} — {reference.url}")

    document.add_heading("Statut", level=3)
    if fiche.statut == "ok":
        document.add_paragraph("OK")
    else:
        document.add_paragraph("À revoir")
        for motif in fiche.motifs:
            _paragraphe(document, f"{motif.code} : {motif.detail}")

    document.add_heading("Traçabilité", level=3)
    _paragraphe(
        document, f"Note : {fiche.tracabilite.note} — Constat type : {fiche.tracabilite.constat_id}"
    )


def _annexe_ecartees(document: Document, ecartees: list[EntreeEcartee]) -> None:
    document.add_heading("Annexe — notes écartées", level=1)
    table = document.add_table(rows=1, cols=3)
    table.style = _style_table(document, "Table Grid")
    entetes = table.rows[0].cells
    for cellule, texte in zip(entetes, ("Note", "Statut", "Motif"), strict=True):
        cellule.text = texte
    for entree in ecartees:
        cellules = table.add_row().cells
        valeurs = (entree.note, entree.statut, f"{entree.motif.code} : {entree.motif.detail}")
        for cellule, texte in zip(cellules, valeurs, strict=True):
            cellule.text = _propre(texte)
