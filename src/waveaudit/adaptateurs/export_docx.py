"""Adaptateur d'export Word (CAP-6, contrats §17, AD-14). Implémente `domaine.ports.Exporteur`.

Le rapport d'incident (CERT, contrats §21) réutilise `BANDEAU` sans modifier ce module.
"""

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.table import Table

from waveaudit.adaptateurs.theme_generique import (
    COULEUR_PRIMAIRE_DEFAUT,
    COULEUR_SECONDAIRE_DEFAUT,
    appliquer_couleurs,
    charger_theme,
    document_generique,
)
from waveaudit.domaine.modeles import EntreeEcartee, Fiche, Rapport

BANDEAU = "Démonstration — données fictives"

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
        self._theme_prive = Path(theme_prive)

    def exporter(self, rapport: Rapport, chemin: Path) -> None:
        theme = charger_theme(self._theme_prive)
        document = self._document_de_depart(theme)

        _bandeau_en_tete_pied(document)
        document.add_heading("Rapport de constats", level=0)
        _table_synthese(document, rapport.fiches)
        for index, fiche in enumerate(rapport.fiches, start=1):
            _section_fiche(document, index, fiche)
        if rapport.ecartees:
            _annexe_ecartees(document, rapport.ecartees)

        chemin = Path(chemin)
        chemin.parent.mkdir(parents=True, exist_ok=True)
        document.save(str(chemin))

    def _document_de_depart(self, theme: dict) -> Document:
        modele = self._theme_prive / "modele.docx"
        if modele.is_file():
            document = Document(str(modele))
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


def _bandeau_en_tete_pied(document: Document) -> None:
    for section in document.sections:
        for conteneur in (section.header, section.footer):
            paragraphe = (
                conteneur.paragraphs[0] if conteneur.paragraphs else conteneur.add_paragraph()
            )
            paragraphe.text = BANDEAU
            paragraphe.alignment = WD_ALIGN_PARAGRAPH.CENTER


def _style_table(document: Document, style_prefere: str) -> str:
    """`style_prefere` s'il existe dans le document (modèle privé), sinon un style générique."""
    if style_prefere in (s.name for s in document.styles):
        return style_prefere
    return "Table Grid"


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
            cellule.text = texte
    return table


def _section_fiche(document: Document, index: int, fiche: Fiche) -> None:
    document.add_heading(f"{index}. {fiche.titre}", level=2)

    document.add_heading("Description", level=3)
    document.add_paragraph(fiche.description)

    document.add_heading("Impact", level=3)
    document.add_paragraph(fiche.impact)

    document.add_heading("Recommandation", level=3)
    document.add_paragraph(fiche.recommandation)

    document.add_heading("CVSS 3.1", level=3)
    document.add_paragraph(
        f"Vecteur : {fiche.cvss.vecteur} — Score : {fiche.cvss.score:.1f} — "
        f"Sévérité : {_SEVERITES_AFFICHEES[fiche.cvss.severite]}"
    )

    document.add_heading("Références", level=3)
    for reference in fiche.references:
        document.add_paragraph(f"{reference.id} — {reference.titre} — {reference.url}")

    document.add_heading("Statut", level=3)
    if fiche.statut == "ok":
        document.add_paragraph("OK")
    else:
        document.add_paragraph("À revoir")
        for motif in fiche.motifs:
            document.add_paragraph(f"{motif.code} : {motif.detail}")

    document.add_heading("Traçabilité", level=3)
    document.add_paragraph(
        f"Note : {fiche.tracabilite.note} — Constat type : {fiche.tracabilite.constat_id}"
    )


def _annexe_ecartees(document: Document, ecartees: list[EntreeEcartee]) -> None:
    document.add_heading("Annexe — notes écartées", level=1)
    table = document.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    entetes = table.rows[0].cells
    for cellule, texte in zip(entetes, ("Note", "Statut", "Motif"), strict=True):
        cellule.text = texte
    for entree in ecartees:
        cellules = table.add_row().cells
        valeurs = (entree.note, entree.statut, f"{entree.motif.code} : {entree.motif.detail}")
        for cellule, texte in zip(cellules, valeurs, strict=True):
            cellule.text = texte
