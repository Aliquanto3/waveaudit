from waveaudit.domaine.cvss31 import evaluer
from waveaudit.domaine.garde_fous import appliquer
from waveaudit.domaine.modeles import (
    Candidat,
    CodeMotif,
    ConstatType,
    Motif,
    Note,
    Reference,
    Statut,
)

VECTEUR_DEFAUT = "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N"
VECTEUR_HAUT = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"


def _constat(**kwargs) -> ConstatType:
    defauts = dict(
        id="WEB-XSS-REFLECHI",
        titre="Injection de script reflétée (XSS)",
        famille="web",
        mots_cles=["xss", "script"],
        description="Description du constat type, assez longue pour passer le garde-fou.",
        impact="Impact du constat type, assez long pour passer le garde-fou de longueur.",
        recommandation="Recommandation du constat type, assez longue pour passer le garde-fou.",
        cvss_vecteur=VECTEUR_DEFAUT,
        references=[
            Reference(
                id="CWE-79", titre="XSS", url="https://cwe.mitre.org/data/definitions/79.html"
            )
        ],
        source="Rédaction WaveAudit, licence du dépôt",
    )
    defauts.update(kwargs)
    return ConstatType(**defauts)


def _note(**kwargs) -> Note:
    defauts = dict(
        fichier="01-xss.md",
        titre=None,
        actif="exemple.test",
        severite_pressentie=None,
        constat_attendu=None,
        corps="Un script passe dans le paramètre de recherche.",
    )
    defauts.update(kwargs)
    return Note(**defauts)


def _candidats() -> list[Candidat]:
    return [Candidat(id="WEB-XSS-REFLECHI", score=3.2)]


def _sortie_nominale() -> dict:
    return {
        "titre": "Le champ de recherche reflète un script sans échappement.",
        "description": "Le paramètre q est renvoyé tel quel, permettant l'exécution de script.",
        "impact": "Un attaquant peut voler la session d'un utilisateur via un lien piégé.",
        "recommandation": "Échapper la sortie HTML et appliquer une politique stricte.",
        "cvss": {
            "AV": "N",
            "AC": "L",
            "PR": "N",
            "UI": "R",
            "S": "C",
            "C": "L",
            "I": "L",
            "A": "N",
        },
    }


def test_appliquer_nominal_statut_ok_sans_motif():
    fiche = appliquer(_sortie_nominale(), _constat(), _note(), _candidats(), 1200)
    assert fiche.statut == Statut.OK
    assert fiche.motifs == []
    assert fiche.cvss.severite == "moyenne"
    assert fiche.tracabilite.note == "01-xss.md"
    assert fiche.tracabilite.constat_id == "WEB-XSS-REFLECHI"
    assert fiche.references == _constat().references


def test_references_du_constat_conservees():
    sortie = _sortie_nominale()
    sortie["description"] += (
        " Voir CWE-79 pour le détail et https://cwe.mitre.org/data/definitions/79.html."
    )
    fiche = appliquer(sortie, _constat(), _note(), _candidats(), 1200)
    assert "CWE-79" in fiche.description
    assert "https://cwe.mitre.org/data/definitions/79.html" in fiche.description
    assert not any(m.code == CodeMotif.REFERENCE_RETIREE for m in fiche.motifs)
    assert fiche.statut == Statut.OK


def test_references_inventees_retirees_casse_ponctuation_url():
    sortie = _sortie_nominale()
    sortie["description"] += " Lié à cwe-9999 et CVE-2099-0001, voir (https://exemple.invalid/x.)."
    fiche = appliquer(sortie, _constat(), _note(), _candidats(), 1200)
    assert "cwe-9999" not in fiche.description.lower()
    assert "CVE-2099-0001" not in fiche.description
    assert "exemple.invalid" not in fiche.description
    details = {m.detail for m in fiche.motifs if m.code == CodeMotif.REFERENCE_RETIREE}
    assert "cwe-9999" in details
    assert "CVE-2099-0001" in details
    assert any("exemple.invalid" in d for d in details)
    assert fiche.statut == Statut.A_REVOIR
    # pas de parenthèses ou crochets vides laissés après nettoyage
    assert "()" not in fiche.description
    assert "[]" not in fiche.description


def test_vecteur_invalide_applique_le_defaut_du_constat():
    sortie = _sortie_nominale()
    sortie["cvss"] = {**sortie["cvss"], "AV": "X"}
    fiche = appliquer(sortie, _constat(), _note(), _candidats(), 1200)
    assert fiche.cvss == evaluer(VECTEUR_DEFAUT)
    assert any(m.code == CodeMotif.VECTEUR_INVALIDE for m in fiche.motifs)
    assert fiche.statut == Statut.A_REVOIR


def test_vecteur_incomplet_applique_le_defaut_du_constat():
    sortie = _sortie_nominale()
    del sortie["cvss"]["A"]
    fiche = appliquer(sortie, _constat(), _note(), _candidats(), 1200)
    assert fiche.cvss == evaluer(VECTEUR_DEFAUT)
    assert any(m.code == CodeMotif.VECTEUR_INVALIDE for m in fiche.motifs)


def test_rubrique_courte_remplacee_par_le_texte_du_constat():
    constat = _constat()
    sortie = _sortie_nominale()
    sortie["impact"] = "Trop court."
    fiche = appliquer(sortie, constat, _note(), _candidats(), 1200)
    assert fiche.impact == constat.impact
    assert any(
        m.code == CodeMotif.RUBRIQUE_COMPLETEE and m.detail == "impact" for m in fiche.motifs
    )
    assert fiche.statut == Statut.A_REVOIR


def test_rubrique_vide_remplacee_par_le_texte_du_constat():
    constat = _constat()
    sortie = _sortie_nominale()
    sortie["recommandation"] = ""
    fiche = appliquer(sortie, constat, _note(), _candidats(), 1200)
    assert fiche.recommandation == constat.recommandation
    assert any(
        m.code == CodeMotif.RUBRIQUE_COMPLETEE and m.detail == "recommandation"
        for m in fiche.motifs
    )


def test_rubrique_trop_longue_tronquee():
    sortie = _sortie_nominale()
    sortie["description"] = "a" * 50
    fiche = appliquer(sortie, _constat(), _note(), _candidats(), 30)
    assert len(fiche.description) == 30
    assert not any(m.code == CodeMotif.RUBRIQUE_COMPLETEE for m in fiche.motifs)


def test_invariant_statut_motifs():
    fiche_ok = appliquer(_sortie_nominale(), _constat(), _note(), _candidats(), 1200)
    assert fiche_ok.statut == Statut.OK
    assert fiche_ok.motifs == []

    sortie_ko = _sortie_nominale()
    sortie_ko["cvss"]["AV"] = "X"
    fiche_ko = appliquer(sortie_ko, _constat(), _note(), _candidats(), 1200)
    assert fiche_ko.statut == Statut.A_REVOIR
    assert fiche_ko.motifs


def test_motifs_initiaux_transmis():
    motif = Motif(code=CodeMotif.NOTE_TRONQUEE, detail="note_tronquee")
    fiche = appliquer(
        _sortie_nominale(),
        _constat(),
        _note(),
        _candidats(),
        1200,
        motifs_initiaux=[motif],
    )
    assert motif in fiche.motifs
    assert fiche.statut == Statut.A_REVOIR


def test_constat_attendu_transmis_dans_la_tracabilite():
    fiche = appliquer(
        _sortie_nominale(),
        _constat(),
        _note(constat_attendu="WEB-XSS-REFLECHI"),
        _candidats(),
        1200,
    )
    assert fiche.tracabilite.constat_attendu == "WEB-XSS-REFLECHI"
