"""Tests de l'extraction d'indicateurs (contrats §21, CAP-4, formats-incident.md)."""

from pathlib import Path

import yaml

from tests.incident_outils import evenement
from waveaudit.domaine.incident import Evenement
from waveaudit.domaine.indicateurs import extraire

FIXTURE = Path(__file__).parents[1] / "donnees" / "incident" / "canoniques.yaml"


def _win(**surcharges):
    donnees = {
        "source": "windows",
        "fichier": "security.json",
        "ligne": 1,
        "event_id": 4624,
        "log_name": "Security",
        "programme": None,
        "message": "Ouverture de session réussie.",
        "champs": {},
    }
    return evenement(**(donnees | surcharges))


def test_extraire_ip_champ_et_message_dedoublonnees():
    e1 = _win(ligne=1, champs={"IpAddress": "192.0.2.10"})
    e2 = evenement(
        ligne=2, message="Failed password for admin from 192.0.2.10 port 4 ssh2", champs={}
    )
    indicateurs = extraire([e1, e2])
    ips = [i for i in indicateurs if i.type == "ip"]
    assert len(ips) == 1
    assert ips[0].valeur == "192.0.2.10"
    assert ips[0].origines == ["auth.log:2", "security.json:1"]


def test_extraire_ipv4_mappee_devient_ipv4():
    e = _win(champs={"IpAddress": "::ffff:192.0.2.10"})
    indicateurs = extraire([e])
    assert [i.valeur for i in indicateurs if i.type == "ip"] == ["192.0.2.10"]


def test_extraire_ip_exclusions():
    evenements = [
        _win(ligne=1, champs={"IpAddress": "0.0.0.0"}),
        _win(ligne=2, champs={"IpAddress": "127.0.0.5"}),
        _win(ligne=3, champs={"IpAddress": "::1"}),
        _win(ligne=4, champs={"IpAddress": "::"}),
        _win(ligne=5, champs={"IpAddress": "pas-une-ip"}),
    ]
    assert [i for i in extraire(evenements) if i.type == "ip"] == []


def test_extraire_compte_casse_et_graphie_premiere():
    e1 = _win(ligne=1, champs={"TargetUserName": "C.Martin"})
    e2 = _win(ligne=2, champs={"TargetUserName": "c.martin"})
    indicateurs = extraire([e1, e2])
    comptes = [i for i in indicateurs if i.type == "compte"]
    assert len(comptes) == 1
    assert comptes[0].valeur == "C.Martin"
    assert comptes[0].origines == ["security.json:1", "security.json:2"]


def test_extraire_compte_exclusions():
    evenements = [
        _win(ligne=1, champs={"TargetUserName": "SYSTEM"}),
        _win(ligne=2, champs={"TargetUserName": "-"}),
        _win(ligne=3, champs={"TargetUserName": "svc-maj$"}),
        _win(ligne=4, champs={"TargetUserName": "Local Service"}),
        _win(ligne=5, champs={"TargetUserName": "Network Service"}),
        _win(ligne=6, champs={"TargetUserName": "Anonymous Logon"}),
        _win(ligne=7, champs={"TargetUserName": ""}),
    ]
    assert [i for i in extraire(evenements) if i.type == "compte"] == []


def test_extraire_compte_groupe_exclut_target_garde_subject():
    e = _win(
        event_id=4732,
        champs={"TargetUserName": "Administrateurs", "SubjectUserName": "administrateur"},
    )
    comptes = {i.valeur for i in extraire([e]) if i.type == "compte"}
    assert comptes == {"administrateur"}


def test_extraire_executable_minuscule():
    e = _win(champs={"Image": r"C:\ProgramData\Maj\Outil.EXE"})
    executables = [i.valeur for i in extraire([e]) if i.type == "executable"]
    assert executables == [r"c:\programdata\maj\outil.exe"]


def test_extraire_hachage_md5_sha1_sha256_minuscules_imphash_ignore():
    e = _win(
        champs={
            "Hashes": (
                "IMPHASH=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA,"
                "MD5=A1B2C3D4A1B2C3D4A1B2C3D4A1B2C3D4,"
                "SHA1=A1B2C3D4A1B2C3D4A1B2C3D4A1B2C3D4A1B2C3D4,"
                "SHA256=A1B2C3D4A1B2C3D4A1B2C3D4A1B2C3D4A1B2C3D4A1B2C3D4A1B2C3D4A1B2C3D4"
            )
        }
    )
    hachages = sorted(i.valeur for i in extraire([e]) if i.type == "hachage")
    assert hachages == [
        "a1b2c3d4a1b2c3d4a1b2c3d4a1b2c3d4",
        "a1b2c3d4a1b2c3d4a1b2c3d4a1b2c3d4a1b2c3d4",
        "a1b2c3d4a1b2c3d4a1b2c3d4a1b2c3d4a1b2c3d4a1b2c3d4a1b2c3d4a1b2c3d4",
    ]


def test_extraire_hote_minuscule():
    e = _win(hote="SRV-FICHIERS")
    assert [i.valeur for i in extraire([e]) if i.type == "hote"] == ["srv-fichiers"]


def test_extraire_resultat_trie_type_puis_valeur():
    e = _win(
        champs={"IpAddress": "192.0.2.10", "TargetUserName": "c.martin"},
        hote="SRV-FICHIERS",
    )
    indicateurs = extraire([e])
    assert [(i.type, i.valeur) for i in indicateurs] == sorted(
        (i.type, i.valeur) for i in indicateurs
    )


def test_extraire_entrees_canoniques_oracle_a_la_main():
    """Revue C4 : fixture `canoniques.yaml` (C1), entrées mélangées, attendu écrit à la main."""
    entrees = {e["id"]: e for e in yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))}
    evenements = [
        Evenement.model_validate(
            entrees[i]["evenement"]
            | {"fichier": entrees[i]["fichier"], "ligne": entrees[i]["ligne"]}
        )
        for i in (
            "chrono-14-win-outil-offensif",
            "chrono-10-win-ajout-groupe-admin",
            "chrono-01-ssh-force-brute",
        )
    ]
    obtenus = [(i.type, i.valeur, i.origines) for i in extraire(evenements)]
    assert obtenus == [
        ("compte", "admin", ["auth.log:1"]),
        ("compte", "administrateur", ["security.json:1"]),
        ("executable", "c:\\programdata\\maj\\outil.exe", ["sysmon.csv:2"]),
        ("hachage", "a1b2c3d4" * 4, ["sysmon.csv:2"]),
        ("hachage", "a1b2c3d4" * 8, ["sysmon.csv:2"]),
        ("hote", "bastion01", ["auth.log:1"]),
        ("hote", "pc-compta07", ["sysmon.csv:2"]),
        ("hote", "srv-fichiers", ["security.json:1"]),
        ("ip", "203.0.113.45", ["auth.log:1"]),
    ]
