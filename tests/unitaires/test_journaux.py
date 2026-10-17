"""Lecture des journaux CERT (CAP-1, contrats §21 « Lecture », C2)."""

from pathlib import Path

import pytest
import yaml

from waveaudit.adaptateurs.journaux import SourceJournauxFichiers
from waveaudit.domaine.erreurs import EntreeInvalide
from waveaudit.domaine.incident import Evenement

FIXTURE = Path(__file__).parents[1] / "donnees" / "incident" / "canoniques.yaml"
ENTREES = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))


def _attendu(entree: dict) -> Evenement:
    return Evenement.model_validate(
        entree["evenement"] | {"fichier": entree["fichier"], "ligne": entree["ligne"]}
    )


@pytest.mark.parametrize("entree", ENTREES, ids=[e["id"] for e in ENTREES])
def test_canonique_lu_a_identique(tmp_path, entree):
    (tmp_path / entree["fichier"]).write_text(entree["brut"], encoding="utf-8")
    lecture = SourceJournauxFichiers().lire(tmp_path, annee=2026)
    attendu = _attendu(entree)
    (correspondant,) = [e for e in lecture.evenements if e.cle == attendu.cle]
    assert correspondant == attendu
    assert lecture.ignorees == []


def test_dossier_absent():
    with pytest.raises(EntreeInvalide):
        SourceJournauxFichiers().lire(Path("introuvable-xyz"), annee=2026)


def test_dossier_sans_fichier_route(tmp_path):
    (tmp_path / "notes.md").write_text("rien à lire", encoding="utf-8")
    (tmp_path / "archive.gz").write_bytes(b"\x1f\x8b")
    with pytest.raises(EntreeInvalide):
        SourceJournauxFichiers().lire(tmp_path, annee=2026)


def test_fichiers_ignores_en_silence(tmp_path):
    (tmp_path / "auth.log").write_text(
        "Oct 14 08:00:00 BASTION01 sshd[1]: Accepted publickey for deploy from"
        " 198.51.100.1 port 1 ssh2\n",
        encoding="utf-8",
    )
    (tmp_path / "archive.gz").write_bytes(b"\x1f\x8b\x00")
    (tmp_path / "regles.yaml").write_text("- id: x\n", encoding="utf-8")
    (tmp_path / "notes.md").write_text("# notes\n", encoding="utf-8")
    (tmp_path / ".cache").write_text("caché", encoding="utf-8")
    lecture = SourceJournauxFichiers().lire(tmp_path, annee=2026)
    assert set(lecture.fichiers) == {"auth.log"}
    assert len(lecture.evenements) == 1


def test_bom_utf16(tmp_path):
    contenu = (
        '[{"TimeCreated": "2026-10-14T09:00:00+02:00", "Id": 4624, "LogName": "Security", '
        '"ProviderName": "p", "MachineName": "SRV01", "Message": "ok", "Data": {}}]'
    )
    (tmp_path / "security.json").write_bytes(contenu.encode("utf-16"))
    lecture = SourceJournauxFichiers().lire(tmp_path, annee=2026)
    assert len(lecture.evenements) == 1
    assert lecture.evenements[0].hote == "SRV01"


def test_bom_utf8(tmp_path):
    contenu = (
        '[{"TimeCreated": "2026-10-14T09:00:00+02:00", "Id": 4624, "LogName": "Security", '
        '"ProviderName": "p", "MachineName": "SRV01", "Message": "ok", "Data": {}}]'
    )
    (tmp_path / "security.json").write_bytes(b"\xef\xbb\xbf" + contenu.encode("utf-8"))
    lecture = SourceJournauxFichiers().lire(tmp_path, annee=2026)
    assert len(lecture.evenements) == 1


def test_csv_separateur_point_virgule(tmp_path):
    (tmp_path / "sysmon.csv").write_text(
        "TimeCreated;Id;LogName;ProviderName;MachineName;Message;Image\n"
        "2026-10-14T08:00:00+02:00;1;Microsoft-Windows-Sysmon/Operational;p;PC01;Process Create;"
        "C:\\Windows\\System32\\calc.exe\n",
        encoding="utf-8",
    )
    lecture = SourceJournauxFichiers().lire(tmp_path, annee=2026)
    assert len(lecture.evenements) == 1
    assert lecture.evenements[0].champs == {"Image": "C:\\Windows\\System32\\calc.exe"}


def test_csv_multiligne_ligne_de_debut(tmp_path):
    """Une valeur CSV multiligne (quottée) décale la ligne de départ du prochain enregistrement."""
    contenu = (
        "TimeCreated,Id,LogName,ProviderName,MachineName,Message,Image\n"
        '2026-10-14T08:00:00+02:00,1,Microsoft-Windows-Sysmon/Operational,p,PC01,"ligne\n'
        'suivante",C:\\Windows\\System32\\calc.exe\n'
        "2026-10-14T08:05:00+02:00,1,Microsoft-Windows-Sysmon/Operational,p,PC01,Process Create,"
        "C:\\Windows\\System32\\notepad.exe\n"
    )
    (tmp_path / "sysmon.csv").write_text(contenu, encoding="utf-8")
    lecture = SourceJournauxFichiers().lire(tmp_path, annee=2026)
    assert len(lecture.evenements) == 2
    premier = next(e for e in lecture.evenements if "calc.exe" in e.champs["Image"])
    second = next(e for e in lecture.evenements if "notepad.exe" in e.champs["Image"])
    assert premier.ligne == 2
    assert second.ligne == 4


def test_json_racine_non_tableau(tmp_path):
    (tmp_path / "security.json").write_text('{"Id": 1}', encoding="utf-8")
    lecture = SourceJournauxFichiers().lire(tmp_path, annee=2026)
    assert lecture.evenements == []
    assert len(lecture.ignorees) == 1
    assert lecture.ignorees[0].ligne == 1


_ENTETE_CSV = "TimeCreated,Id,LogName,ProviderName,MachineName,Message,Image"
_ENREGISTREMENT_CSV = (
    "2026-10-14T08:0{m}:00+02:00,1,Microsoft-Windows-Sysmon/Operational,p,PC01,m,C:\\x{m}.exe"
)


@pytest.mark.parametrize("fin", ["\r\r\n", "\r\n", "\n", "\r"], ids=["CRCRLF", "CRLF", "LF", "CR"])
def test_csv_ligne_physique_quelle_que_soit_la_fin_de_ligne(tmp_path, fin):
    """Revue C2 : `\\r\\r\\n` doublait les numéros de ligne (csv compte chaque `\\r`)."""
    lignes = [_ENTETE_CSV] + [_ENREGISTREMENT_CSV.format(m=m) for m in (1, 2, 3)]
    (tmp_path / "sysmon.csv").write_bytes((fin.join(lignes) + fin).encode("utf-8"))
    lecture = SourceJournauxFichiers().lire(tmp_path, annee=2026)
    assert lecture.ignorees == []
    assert [(e.ligne, e.champs["Image"]) for e in lecture.evenements] == [
        (2, "C:\\x1.exe"),
        (3, "C:\\x2.exe"),
        (4, "C:\\x3.exe"),
    ]


@pytest.mark.parametrize("nom", ["security.json", "sysmon.csv"])
def test_windows_non_utf8_ecarte_sans_exception(tmp_path, nom):
    """Revue C2 : un export cp1252 levait UnicodeDecodeError et faisait échouer le lot."""
    contenu = (
        '[{"TimeCreated": "2026-10-14T08:00:00+02:00", "Id": 4624, "MachineName": "PC01",'
        ' "Message": "Ouverture réussie", "Data": {}}]'
        if nom.endswith(".json")
        else f"{_ENTETE_CSV}\n2026-10-14T08:00:00+02:00,1,L,p,PC01,créé,C:\\x.exe\n"
    )
    (tmp_path / nom).write_bytes(contenu.encode("cp1252"))
    lecture = SourceJournauxFichiers().lire(tmp_path, annee=2026)
    assert lecture.evenements == []
    assert [(i.fichier, i.ligne) for i in lecture.ignorees] == [(nom, 1)]
    assert "encodage" in lecture.ignorees[0].raison


def test_utf16_sans_bom_motif_explicite(tmp_path):
    contenu = f"{_ENTETE_CSV}\n{_ENREGISTREMENT_CSV.format(m=1)}\n"
    (tmp_path / "sysmon.csv").write_bytes(contenu.encode("utf-16-le"))
    lecture = SourceJournauxFichiers().lire(tmp_path, annee=2026)
    assert lecture.evenements == []
    assert len(lecture.ignorees) == 1
    assert "NUL" in lecture.ignorees[0].raison


def test_csv_id_chiffre_non_ascii_ignore(tmp_path):
    """Revue C2 : `"²".isdigit()` est vrai mais `int("²")` lève ValueError."""
    contenu = f"{_ENTETE_CSV}\n2026-10-14T08:00:00+02:00,²,L,p,PC01,m,C:\\x.exe\n"
    (tmp_path / "sysmon.csv").write_text(contenu, encoding="utf-8")
    lecture = SourceJournauxFichiers().lire(tmp_path, annee=2026)
    assert lecture.evenements == []
    assert [i.ligne for i in lecture.ignorees] == [2]


def test_lignes_illisibles_comptees(tmp_path):
    (tmp_path / "auth.log").write_text(
        "Oct 14 08:00:00 BASTION01 sshd[1]: Accepted publickey for deploy from"
        " 198.51.100.1 port 1 ssh2\n"
        "une ligne totalement incompréhensible\n",
        encoding="utf-8",
    )
    lecture = SourceJournauxFichiers().lire(tmp_path, annee=2026)
    assert len(lecture.evenements) == 1
    assert len(lecture.ignorees) == 1
    assert lecture.fichiers["auth.log"] == 2


def test_jour_sur_un_seul_chiffre_avec_espace(tmp_path):
    (tmp_path / "auth.log").write_text(
        "Oct  5 08:00:00 BASTION01 sshd[1]: Accepted publickey for deploy from"
        " 198.51.100.1 port 1 ssh2\n",
        encoding="utf-8",
    )
    lecture = SourceJournauxFichiers().lire(tmp_path, annee=2026)
    assert len(lecture.evenements) == 1
    assert lecture.evenements[0].horodatage.day == 5


def test_sudo_sans_pid(tmp_path):
    (tmp_path / "auth.log").write_text(
        "Oct 14 08:00:00 BASTION01 sudo: deploy : TTY=pts/0 ; PWD=/home/deploy ; USER=root ;"
        " COMMAND=/bin/bash\n",
        encoding="utf-8",
    )
    lecture = SourceJournauxFichiers().lire(tmp_path, annee=2026)
    assert len(lecture.evenements) == 1
    evenement = lecture.evenements[0]
    assert evenement.programme == "sudo"
    assert evenement.champs == {"utilisateur": "deploy", "commande": "/bin/bash"}


def test_ligne_iso_rsyslog(tmp_path):
    (tmp_path / "auth.log").write_text(
        "2026-10-14T07:55:00+02:00 BASTION01 sshd[700]: Accepted publickey for deploy from"
        " 198.51.100.20 port 50300 ssh2\n",
        encoding="utf-8",
    )
    lecture = SourceJournauxFichiers().lire(tmp_path, annee=2026)
    assert len(lecture.evenements) == 1
    assert lecture.evenements[0].horodatage.isoformat() == "2026-10-14T07:55:00+02:00"


def test_passage_annee(tmp_path):
    (tmp_path / "auth.log").write_text(
        "Dec 31 23:59:00 BASTION01 sshd[1]: Accepted publickey for deploy from"
        " 198.51.100.1 port 1 ssh2\n"
        "Jan  1 00:00:30 BASTION01 sshd[2]: Accepted publickey for deploy from"
        " 198.51.100.1 port 2 ssh2\n",
        encoding="utf-8",
    )
    lecture = SourceJournauxFichiers().lire(tmp_path, annee=2026)
    assert len(lecture.evenements) == 2
    annees = sorted(e.horodatage.year for e in lecture.evenements)
    assert annees == [2026, 2027]


def test_29_fevrier_annee_non_bissextile(tmp_path):
    (tmp_path / "auth.log").write_text(
        "Feb 29 10:00:00 BASTION01 sshd[1]: Accepted publickey for deploy from"
        " 198.51.100.1 port 1 ssh2\n",
        encoding="utf-8",
    )
    lecture = SourceJournauxFichiers().lire(tmp_path, annee=2026)
    assert lecture.evenements == []
    assert len(lecture.ignorees) == 1


def test_routage_casse_mixte(tmp_path):
    (tmp_path / "Security.JSON").write_text(
        '[{"TimeCreated": "2026-10-14T09:00:00+02:00", "Id": 4624, "LogName": "Security", '
        '"ProviderName": "p", "MachineName": "SRV01", "Message": "ok", "Data": {}}]',
        encoding="utf-8",
    )
    (tmp_path / "AUTH.LOG").write_text(
        "Oct 14 08:00:00 BASTION01 sshd[1]: Accepted publickey for deploy from"
        " 198.51.100.1 port 1 ssh2\n",
        encoding="utf-8",
    )
    lecture = SourceJournauxFichiers().lire(tmp_path, annee=2026)
    assert len(lecture.evenements) == 2
    assert {e.source for e in lecture.evenements} == {"windows", "linux"}


def test_gz_et_yaml_ignores_en_silence(tmp_path):
    (tmp_path / "auth.log").write_text(
        "Oct 14 08:00:00 BASTION01 sshd[1]: Accepted publickey for deploy from"
        " 198.51.100.1 port 1 ssh2\n",
        encoding="utf-8",
    )
    (tmp_path / "auth.log.gz").write_bytes(b"\x1f\x8b\x00")
    (tmp_path / "regles.yaml").write_text("- id: x\n", encoding="utf-8")
    lecture = SourceJournauxFichiers().lire(tmp_path, annee=2026)
    assert set(lecture.fichiers) == {"auth.log"}


def test_tri_final(tmp_path):
    (tmp_path / "auth.log").write_text(
        "Oct 14 08:05:00 BASTION01 sshd[2]: Accepted publickey for deploy from"
        " 198.51.100.1 port 2 ssh2\n"
        "Oct 14 08:00:00 BASTION01 sshd[1]: Accepted publickey for deploy from"
        " 198.51.100.1 port 1 ssh2\n",
        encoding="utf-8",
    )
    lecture = SourceJournauxFichiers().lire(tmp_path, annee=2026)
    horodatages = [e.horodatage for e in lecture.evenements]
    assert horodatages == sorted(horodatages)
