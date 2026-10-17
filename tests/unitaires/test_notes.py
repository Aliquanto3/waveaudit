"""Tests de l'adaptateur de notes brutes (CAP-1, contrats §14, §16)."""

from pathlib import Path

import pytest

from waveaudit.adaptateurs.notes_fichiers import NotesFichiers
from waveaudit.application.config import racine_projet
from waveaudit.domaine.erreurs import EntreeInvalide
from waveaudit.domaine.modeles import Note, NoteInvalide

DOSSIER_DEMO = racine_projet() / "donnees" / "demo" / "notes"
DOSSIER_FIXTURES = Path(__file__).resolve().parents[1] / "donnees" / "notes"

FAMILLES_FIGEES = {
    "web": {
        "WEB-XSS-REFLECHI",
        "WEB-XSS-STOCKE",
        "WEB-INJECTION-SQL",
        "WEB-CSRF",
        "WEB-IDOR",
        "WEB-SSRF",
        "WEB-TRAVERSEE-CHEMIN",
        "WEB-UPLOAD-NON-RESTREINT",
        "WEB-SESSION-FIXATION",
        "WEB-ENTETES-SECURITE",
        "WEB-CORS-PERMISSIF",
        "WEB-REDIRECTION-OUVERTE",
        "WEB-DIVULGATION-ERREURS",
        "WEB-AUTH-FORCE-BRUTE",
        "WEB-XXE",
        "WEB-DESERIALISATION",
    },
    "ad": {
        "AD-KERBEROASTING",
        "AD-ASREP-ROASTING",
        "AD-DELEGATION-NON-CONTRAINTE",
        "AD-LAPS-ABSENT",
        "AD-ADMINS-EXCESSIFS",
        "AD-GPP-MOT-DE-PASSE",
    },
    "infra": {
        "INFRA-SMB-SIGNATURE",
        "INFRA-SERVICE-OBSOLETE",
        "INFRA-SNMP-COMMUNAUTE",
        "INFRA-RDP-EXPOSE",
        "INFRA-LLMNR-NBTNS",
    },
    "config": {
        "CONFIG-MOT-DE-PASSE-DEFAUT",
        "CONFIG-SECRETS-EN-CLAIR",
        "CONFIG-LISTAGE-REPERTOIRE",
        "CONFIG-DEBUG-ACTIF",
    },
    "crypto": {"CRYPTO-TLS-OBSOLETE", "CRYPTO-CERTIFICAT-INVALIDE", "CRYPTO-HACHAGE-FAIBLE"},
    "autre": {"AUTRE-JOURNALISATION-INSUFFISANTE"},
}
IDENTIFIANTS_FIGES = {i for famille in FAMILLES_FIGEES.values() for i in famille}


def _famille(identifiant: str) -> str:
    return identifiant.split("-", 1)[0].lower()


def _trouver(resultats: list[Note | NoteInvalide], nom: str) -> Note | NoteInvalide:
    for element in resultats:
        if element.fichier == nom:
            return element
    raise AssertionError(f"note {nom} absente du résultat")


# --- Notes de démonstration (contrats §16) ----------------------------------------------------


def test_les_20_notes_de_demonstration_sont_valides():
    resultats = NotesFichiers().lire(DOSSIER_DEMO)
    assert len(resultats) == 20
    assert all(isinstance(r, Note) for r in resultats)


def test_les_20_notes_ont_un_constat_attendu_distinct_et_fige():
    notes = NotesFichiers().lire(DOSSIER_DEMO)
    attendus = [n.constat_attendu for n in notes]
    assert all(a is not None for a in attendus)
    assert len(set(attendus)) == 20
    assert set(attendus) <= IDENTIFIANTS_FIGES


def test_les_20_notes_couvrent_les_familles_minimales():
    notes = NotesFichiers().lire(DOSSIER_DEMO)
    par_famille: dict[str, int] = {}
    for note in notes:
        par_famille[_famille(note.constat_attendu)] = (
            par_famille.get(_famille(note.constat_attendu), 0) + 1
        )
    assert par_famille.get("ad", 0) >= 3
    assert par_famille.get("infra", 0) >= 2
    assert par_famille.get("crypto", 0) >= 2
    assert par_famille.get("config", 0) >= 2


def test_les_notes_de_demonstration_ne_citent_jamais_le_constat_ni_de_cwe():
    for note in NotesFichiers().lire(DOSSIER_DEMO):
        assert "cwe" not in note.corps.lower(), note.fichier
        assert note.constat_attendu.lower() not in note.corps.lower(), note.fichier
        assert note.constat_attendu.lower() not in (note.titre or "").lower(), note.fichier


def test_les_notes_de_demonstration_utilisent_des_preuves_fictives():
    corps = "\n".join(n.corps for n in NotesFichiers().lire(DOSSIER_DEMO))
    assert "exemple.test" in corps or ".local" in corps
    assert "192.0.2." in corps


def test_fichiers_de_demonstration_nommes_selon_le_contrat():
    for note in NotesFichiers().lire(DOSSIER_DEMO):
        prefixe, reste = note.fichier.split("-", 1)
        assert prefixe.isdigit() and len(prefixe) == 2, note.fichier
        assert reste.endswith(".md"), note.fichier


def test_note_hors_sujet_est_valide_mais_sans_constat_attendu():
    note = NotesFichiers().lire(DOSSIER_FIXTURES)
    hors_sujet = _trouver(note, "hors-sujet.md")
    assert isinstance(hors_sujet, Note)
    assert hors_sujet.constat_attendu is None


# --- Sélection et tri des fichiers (contrats §14) ---------------------------------------------


def test_dossier_absent_leve_entree_invalide(tmp_path: Path):
    with pytest.raises(EntreeInvalide, match="introuvable"):
        NotesFichiers().lire(tmp_path / "absent")


def test_dossier_sans_note_leve_entree_invalide(tmp_path: Path):
    (tmp_path / "ignore.png").write_bytes(b"x")
    with pytest.raises(EntreeInvalide, match="aucune note"):
        NotesFichiers().lire(tmp_path)


def test_fichier_png_est_ignore():
    resultats = NotesFichiers().lire(DOSSIER_FIXTURES)
    assert all(r.fichier != "ignoree.png" for r in resultats)


def test_extension_insensible_a_la_casse_et_txt_accepte(tmp_path: Path):
    (tmp_path / "A.MD").write_text("corps a", encoding="utf-8")
    (tmp_path / "b.txt").write_text("corps b", encoding="utf-8")
    resultats = NotesFichiers().lire(tmp_path)
    assert {r.fichier for r in resultats} == {"A.MD", "b.txt"}


def test_tri_par_casefold_insensible_a_la_casse(tmp_path: Path):
    (tmp_path / "B.md").write_text("corps b", encoding="utf-8")
    (tmp_path / "a.md").write_text("corps a", encoding="utf-8")
    resultats = NotesFichiers().lire(tmp_path)
    assert [r.fichier for r in resultats] == ["a.md", "B.md"]


def test_ne_descend_pas_dans_les_sous_dossiers(tmp_path: Path):
    (tmp_path / "racine.md").write_text("corps racine", encoding="utf-8")
    sous_dossier = tmp_path / "sous"
    sous_dossier.mkdir()
    (sous_dossier / "cache.md").write_text("corps caché", encoding="utf-8")
    resultats = NotesFichiers().lire(tmp_path)
    assert [r.fichier for r in resultats] == ["racine.md"]


# --- Cas invalides (contrats §14) -------------------------------------------------------------


def test_corps_vide_est_une_note_invalide():
    resultat = _trouver(NotesFichiers().lire(DOSSIER_FIXTURES), "corps-vide.md")
    assert isinstance(resultat, NoteInvalide)
    assert "vide" in resultat.raison


def test_yaml_casse_est_une_note_invalide():
    resultat = _trouver(NotesFichiers().lire(DOSSIER_FIXTURES), "yaml-casse.md")
    assert isinstance(resultat, NoteInvalide)


def test_entete_non_mapping_est_une_note_invalide():
    resultat = _trouver(NotesFichiers().lire(DOSSIER_FIXTURES), "entete-non-mapping.md")
    assert isinstance(resultat, NoteInvalide)
    assert "mapping" in resultat.raison


def test_severite_hors_liste_devient_none_sans_invalider_la_note():
    resultat = _trouver(NotesFichiers().lire(DOSSIER_FIXTURES), "severite-hors-liste.md")
    assert isinstance(resultat, Note)
    assert resultat.severite_pressentie is None
    assert resultat.titre == "Note avec une sévérité pressentie non reconnue"


def test_encodage_invalide_est_une_note_invalide(tmp_path: Path):
    (tmp_path / "mauvais-encodage.md").write_bytes(b"\xff\xfe\xfd\xfc")
    resultat = _trouver(NotesFichiers().lire(tmp_path), "mauvais-encodage.md")
    assert isinstance(resultat, NoteInvalide)


def test_entete_non_refermee_est_une_note_invalide(tmp_path: Path):
    (tmp_path / "entete-ouverte.md").write_text(
        "---\ntitre: pas de fermeture\ncorps réel", encoding="utf-8"
    )
    resultat = _trouver(NotesFichiers().lire(tmp_path), "entete-ouverte.md")
    assert isinstance(resultat, NoteInvalide)


# --- Tolérance et robustesse de lecture --------------------------------------------------------


def test_champ_inconnu_est_ignore_sans_invalider_la_note(tmp_path: Path):
    (tmp_path / "champ-inconnu.md").write_text(
        "---\ntitre: t\nauteur: quelqu'un\n---\ncorps réel de la note",
        encoding="utf-8",
    )
    resultat = _trouver(NotesFichiers().lire(tmp_path), "champ-inconnu.md")
    assert isinstance(resultat, Note)
    assert resultat.titre == "t"


def test_note_sans_entete_est_valide_avec_champs_a_none(tmp_path: Path):
    (tmp_path / "sans-entete.md").write_text("juste du corps, sans en-tête", encoding="utf-8")
    resultat = _trouver(NotesFichiers().lire(tmp_path), "sans-entete.md")
    assert isinstance(resultat, Note)
    assert resultat.titre is None
    assert resultat.corps == "juste du corps, sans en-tête"


def test_bom_et_crlf_sont_tolerés(tmp_path: Path):
    brut = "---\r\ntitre: note avec bom et crlf\r\n---\r\ncorps en crlf\r\nsur deux lignes"
    (tmp_path / "bom-crlf.md").write_bytes(b"\xef\xbb\xbf" + brut.encode("utf-8"))
    resultat = _trouver(NotesFichiers().lire(tmp_path), "bom-crlf.md")
    assert isinstance(resultat, Note)
    assert resultat.titre == "note avec bom et crlf"
    assert resultat.corps == "corps en crlf\nsur deux lignes"
