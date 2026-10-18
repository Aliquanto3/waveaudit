"""Service d'export final et brouillon d'un lot (contrats §27, CAP-13, CAP-17)."""

import json
import threading
from datetime import datetime
from pathlib import Path

import pytest
from docx import Document

from waveaudit.application import composition, export, relecture
from waveaudit.application.lot import dossier_sorties
from waveaudit.domaine.modeles import (
    Candidat,
    Cvss,
    Fiche,
    Note,
    Reference,
    Statut,
    Tracabilite,
)
from waveaudit.domaine.relecture import FicheCorrigee, RefusRelecture, corriger, valider

VECTEUR = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
CVSS = Cvss(vecteur=VECTEUR, score=9.8, severite="critique")
REF = Reference(id="CWE-89", titre="Injection SQL", url="https://cwe.mitre.org/data/89")
CANDIDATS = [Candidat(id="WEB-001", score=3.2)]
# pid improbable : jamais celui du processus de test (`os.getpid()`).
PID_INTROUVABLE = 999_999_999


def _note(fichier: str) -> Note:
    return Note(
        fichier=fichier,
        titre="Injection",
        actif=None,
        severite_pressentie=None,
        constat_attendu="WEB-001",
        corps="Paramètre id injectable.",
    )


def _fiche(note: str, titre: str = "Injection SQL") -> Fiche:
    return Fiche(
        titre=titre,
        description="d" * 30,
        impact="i" * 30,
        recommandation="r" * 30,
        cvss=CVSS,
        references=[REF],
        statut=Statut.OK,
        motifs=[],
        tracabilite=Tracabilite(
            note=note, constat_id="WEB-001", candidats=CANDIDATS, constat_attendu=None
        ),
    )


def _dossier(config, id_lot: str) -> Path:
    dossier = dossier_sorties(config) / id_lot
    dossier.mkdir(parents=True, exist_ok=True)
    return dossier


def _ecrire_lot_json(dossier: Path, **champs: object) -> None:
    base = {
        "id_lot": dossier.name,
        "workflow": "fiches",
        "langue": "fr",
        "modele_demande": None,
        "cree_le": datetime.now().astimezone().isoformat(),
        "pid": PID_INTROUVABLE,
    }
    (dossier / "lot.json").write_text(
        json.dumps(base | champs, ensure_ascii=False), encoding="utf-8"
    )


def _lot(config, id_lot: str, notes: list[str], *, langue: str = "fr") -> Path:
    """Lot `fiches` avec une entrée `attente` par note de `notes` (contrats §25)."""
    dossier = _dossier(config, id_lot)
    _ecrire_lot_json(dossier, langue=langue)
    relecture.initialiser(
        dossier,
        id_lot=id_lot,
        langue=langue,
        modele="externe",
        modele_demande=None,
        elements=[_note(n) for n in notes],
    )
    return dossier


def _textes(chemin: Path) -> str:
    return "\n".join(p.text for p in Document(str(chemin)).paragraphs)


# --- Refus ------------------------------------------------------------------------------------


def test_lot_inconnu(config_test):
    with pytest.raises(RefusRelecture) as refus:
        export.exporter_lot(config_test, "jamais-cree", "final")
    assert refus.value.code == "lot_inconnu"


def test_lot_incident(config_test):
    dossier = _dossier(config_test, "incident-1")
    _ecrire_lot_json(dossier, workflow="incident")
    with pytest.raises(RefusRelecture) as refus:
        export.exporter_lot(config_test, "incident-1", "final")
    assert refus.value.code == "lot_incident"


def test_lot_incident_v010_sans_lot_json(config_test):
    """[revue E18] Lot incident v0.1.0, reconnu par `incident.json` seul (§30)."""
    dossier = _dossier(config_test, "incident-v010")
    (dossier / "incident.json").write_text("{}", encoding="utf-8")
    with pytest.raises(RefusRelecture) as refus:
        export.exporter_lot(config_test, "incident-v010", "brouillon")
    assert refus.value.code == "lot_incident"


def test_lot_en_cours_pid_vivant_externe(config_test, monkeypatch):
    """[revue A13/E13] pid vivant d'un autre processus, sans événement de fin (§30)."""
    dossier = _lot(config_test, "lot-en-cours", ["01.md"])
    monkeypatch.setattr(composition, "processus_actif", lambda pid, cree_le: True)
    with pytest.raises(RefusRelecture) as refus:
        export.exporter_lot(config_test, "lot-en-cours", "final")
    assert refus.value.code == "lot_en_cours"
    assert not list(dossier.glob("rapport-*.docx"))


def test_lot_en_cours_dans_ce_processus(config_test):
    """[revue X2] §27 étape 3 : verrou de ce processus (route web), pid = `os.getpid()`."""
    import os

    from waveaudit.application.moteur_demande import Occupation

    dossier = _lot(config_test, "lot-local", ["01.md"])
    _ecrire_lot_json(dossier, pid=os.getpid())
    relecture.enregistrer_resultat(dossier, 1, _fiche("01.md"))
    relecture.modifier(dossier, 1, 2, valider)
    occupation = Occupation(
        nature="fiches", id_lot="lot-local", index=None, debut=datetime.now().astimezone()
    )
    with pytest.raises(RefusRelecture) as refus:
        export.exporter_lot(config_test, "lot-local", "final", occupation=occupation)
    assert refus.value.code == "lot_en_cours"
    assert not list(dossier.glob("rapport-*.docx"))
    # Régénération d'une fiche de ce lot dans ce processus : refusée aussi (§26).
    regen = Occupation(nature="regeneration", id_lot="lot-local", index=1, debut=occupation.debut)
    with pytest.raises(RefusRelecture) as refus:
        export.exporter_lot(config_test, "lot-local", "final", occupation=regen)
    assert refus.value.code == "lot_en_cours"
    # Une occupation d'un autre lot ne bloque pas celui-ci.
    autre = Occupation(nature="fiches", id_lot="autre", index=None, debut=occupation.debut)
    chemin, _n = export.exporter_lot(config_test, "lot-local", "final", occupation=autre)
    assert chemin.is_file()


def test_aucune_fiche_validee(config_test):
    dossier = _lot(config_test, "lot-sans-validation", ["01.md"])
    relecture.enregistrer_resultat(dossier, 1, _fiche("01.md"))

    with pytest.raises(RefusRelecture) as refus:
        export.exporter_lot(config_test, "lot-sans-validation", "final")
    assert refus.value.code == "aucune_fiche_validee"


# --- Export final et brouillon -----------------------------------------------------------------


def test_final_avec_fiche_validee_dans_sa_version_corrigee(config_test):
    dossier = _lot(config_test, "lot-corrige", ["01.md"])
    relecture.enregistrer_resultat(dossier, 1, _fiche("01.md"))
    correction = FicheCorrigee(
        titre="Faille corrigée",
        description="d" * 30,
        impact="i" * 30,
        recommandation="r" * 30,
        cvss_vecteur=VECTEUR,
        cvss=CVSS,
        references=[REF],
    )
    relecture.modifier(dossier, 1, 2, lambda e: corriger(e, correction, 4000))
    relecture.modifier(dossier, 1, 3, valider)

    chemin, non_validees = export.exporter_lot(config_test, "lot-corrige", "final")

    assert chemin == dossier / "rapport-lot-corrige.docx"
    assert non_validees == 0
    texte = _textes(chemin)
    assert "Faille corrigée" in texte
    assert "Non validée" not in texte


def test_brouillon_avec_marque_et_langue_du_lot(config_test):
    dossier = _lot(config_test, "lot-brouillon", ["01.md"], langue="en")
    relecture.enregistrer_resultat(dossier, 1, _fiche("01.md"))  # jamais validée

    chemin, non_validees = export.exporter_lot(config_test, "lot-brouillon", "brouillon")

    assert chemin == dossier / "brouillon-lot-brouillon.docx"
    assert non_validees == 1
    texte = _textes(chemin)
    assert "Findings report" in texte  # libellés anglais (langue du lot)
    assert "Not validated" in texte  # marque de brouillon


def test_ecrasement_a_chaque_export(config_test):
    dossier = _lot(config_test, "lot-ecrase", ["01.md"])
    relecture.enregistrer_resultat(dossier, 1, _fiche("01.md"))

    chemin_1, _ = export.exporter_lot(config_test, "lot-ecrase", "brouillon")
    chemin_2, _ = export.exporter_lot(config_test, "lot-ecrase", "brouillon")

    assert chemin_1 == chemin_2
    assert len(list(dossier.glob("brouillon-*.docx"))) == 1


def test_nombre_de_non_validees_renvoye(config_test):
    dossier = _lot(config_test, "lot-mixte", ["01.md", "02.md"])
    relecture.enregistrer_resultat(dossier, 1, _fiche("01.md"))
    relecture.enregistrer_resultat(dossier, 2, _fiche("02.md"))
    relecture.modifier(dossier, 1, 2, valider)  # 01 validée, 02 non validée

    _, non_validees_final = export.exporter_lot(config_test, "lot-mixte", "final")
    _, non_validees_brouillon = export.exporter_lot(config_test, "lot-mixte", "brouillon")

    assert non_validees_final == 1
    assert non_validees_brouillon == 1


def test_aucun_partiel_restant(config_test):
    dossier = _lot(config_test, "lot-partiel", ["01.md"])
    relecture.enregistrer_resultat(dossier, 1, _fiche("01.md"))

    export.exporter_lot(config_test, "lot-partiel", "brouillon")

    assert not list(dossier.glob(".*.partiel"))


def test_deux_exports_simultanes_sans_melange(config_test):
    dossier = _lot(config_test, "lot-concurrent", ["01.md"])
    relecture.enregistrer_resultat(dossier, 1, _fiche("01.md"))
    erreurs: list[Exception] = []

    def exporter() -> None:
        try:
            export.exporter_lot(config_test, "lot-concurrent", "brouillon")
        except Exception as erreur:  # noqa: BLE001 - toute exception est une régression du test
            erreurs.append(erreur)

    threads = [threading.Thread(target=exporter) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not erreurs
    assert not list(dossier.glob(".*.partiel"))
    assert len(list(dossier.glob("brouillon-*.docx"))) == 1
