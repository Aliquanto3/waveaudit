"""Tests de l'export Word (CAP-6, contrats §17, AD-14)."""

from pathlib import Path

from docx import Document

from waveaudit.adaptateurs.export_docx import BANDEAU, ExportDocx
from waveaudit.domaine.modeles import (
    Candidat,
    CodeMotif,
    Cvss,
    EntreeEcartee,
    Fiche,
    Motif,
    Rapport,
    Reference,
    Statut,
    Tracabilite,
)

_REFERENCE = Reference(
    id="CWE-79", titre="XSS", url="https://cwe.mitre.org/data/definitions/79.html"
)


def _fiche_ok() -> Fiche:
    return Fiche(
        titre="Injection SQL sur le formulaire de connexion",
        description="La requête concatène l'entrée utilisateur sans échappement.",
        impact="Contournement de l'authentification, lecture de la base.",
        recommandation="Utiliser des requêtes paramétrées.",
        cvss=Cvss(
            vecteur="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H", score=9.8, severite="critique"
        ),
        references=[_REFERENCE],
        statut=Statut.OK,
        motifs=[],
        tracabilite=Tracabilite(
            note="01-injection-sql.md",
            constat_id="WEB-INJECTION-SQL",
            candidats=[Candidat(id="WEB-INJECTION-SQL", score=0.9)],
            constat_attendu="WEB-INJECTION-SQL",
        ),
    )


def _fiche_a_revoir() -> Fiche:
    return Fiche(
        titre="Vecteur CVSS invalide",
        description="d",
        impact="i",
        recommandation="r",
        cvss=Cvss(
            vecteur="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:N", score=0.0, severite="aucune"
        ),
        references=[_REFERENCE],
        statut=Statut.A_REVOIR,
        motifs=[Motif(code=CodeMotif.VECTEUR_INVALIDE, detail="métrique AC inconnue : X")],
        tracabilite=Tracabilite(
            note="02-notes.md",
            constat_id="WEB-XSS-REFLECHI",
            candidats=[Candidat(id="WEB-XSS-REFLECHI", score=0.4)],
            constat_attendu=None,
        ),
    )


def _rapport(avec_ecartees: bool) -> Rapport:
    ecartees = (
        [
            EntreeEcartee(
                note="03-hors-sujet.md",
                statut=Statut.NON_RATTACHEE,
                motif=Motif(
                    code=CodeMotif.AUCUN_CONSTAT, detail="aucun candidat au-dessus du seuil"
                ),
                candidats=[],
                constat_attendu=None,
            ),
            EntreeEcartee(
                note="04-invalide.md",
                statut=Statut.NON_TRAITEE,
                motif=Motif(code=CodeMotif.NOTE_INVALIDE, detail="corps vide"),
                candidats=[],
                constat_attendu=None,
            ),
        ]
        if avec_ecartees
        else []
    )
    return Rapport(fiches=[_fiche_ok(), _fiche_a_revoir()], ecartees=ecartees)


def _textes(document: Document) -> list[str]:
    return [p.text for p in document.paragraphs]


def test_theme_generique_sans_dossier_produit_un_rapport_complet(tmp_path: Path):
    chemin = tmp_path / "sortie" / "rapport.docx"
    ExportDocx(tmp_path / "theme-prive-absent").exporter(_rapport(avec_ecartees=True), chemin)

    assert chemin.is_file()
    document = Document(str(chemin))

    for section in document.sections:
        assert section.header.paragraphs[0].text == BANDEAU
        assert section.footer.paragraphs[0].text == BANDEAU

    titres = [
        p.text
        for p in document.paragraphs
        if p.style.name.startswith("Heading") or p.style.name == "Title"
    ]
    assert "Rapport de constats" in titres
    assert "1. Injection SQL sur le formulaire de connexion" in titres
    assert "2. Vecteur CVSS invalide" in titres
    intitules = (
        "Description",
        "Impact",
        "Recommandation",
        "CVSS 3.1",
        "Références",
        "Statut",
        "Traçabilité",
    )
    for intitule in intitules:
        assert titres.count(intitule) == 2
    assert "Annexe — notes écartées" in titres

    textes = _textes(document)
    assert "À revoir" in textes
    assert any("vecteur_invalide : métrique AC inconnue : X" in t for t in textes)

    tables = document.tables
    assert len(tables) == 2
    synthese = [cellule.text for cellule in tables[0].rows[0].cells]
    assert synthese == ["N°", "Titre", "Sévérité", "Score", "Statut"]
    ligne_ok = [cellule.text for cellule in tables[0].rows[1].cells]
    assert ligne_ok[-1] == "OK"
    ligne_a_revoir = [cellule.text for cellule in tables[0].rows[2].cells]
    assert ligne_a_revoir[-1] == "À revoir"

    annexe = [cellule.text for cellule in tables[1].rows[0].cells]
    assert annexe == ["Note", "Statut", "Motif"]
    assert tables[1].rows[1].cells[0].text == "03-hors-sujet.md"


def test_sans_ecartees_pas_dannexe(tmp_path: Path):
    chemin = tmp_path / "rapport.docx"
    ExportDocx(tmp_path / "theme-prive-absent").exporter(_rapport(avec_ecartees=False), chemin)

    document = Document(str(chemin))
    titres = [p.text for p in document.paragraphs]
    assert "Annexe — notes écartées" not in titres
    assert len(document.tables) == 1


def test_theme_prive_avec_modele_et_theme_toml(tmp_path: Path):
    theme_prive = tmp_path / "theme-prive"
    theme_prive.mkdir()
    Document().save(str(theme_prive / "modele.docx"))
    (theme_prive / "theme.toml").write_text(
        'couleur_primaire = "#123456"\ncle_inconnue = "ignoree"\n', encoding="utf-8"
    )

    chemin = tmp_path / "rapport.docx"
    ExportDocx(theme_prive).exporter(_rapport(avec_ecartees=False), chemin)

    document = Document(str(chemin))
    assert document.styles["Heading 1"].font.color.rgb is not None
    assert str(document.styles["Heading 1"].font.color.rgb) == "123456"
    titres = [p.text for p in document.paragraphs]
    assert "Rapport de constats" in titres
