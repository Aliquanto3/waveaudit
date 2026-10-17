import os
import subprocess
import sys

import pytest

from waveaudit.interfaces import cli


def test_main_lance_app(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["waveaudit", "version"])
    with pytest.raises(SystemExit) as sortie:
        cli.main()
    assert sortie.value.code == 0
    assert capsys.readouterr().out.startswith("waveaudit ")


def test_script_sortie_utf8():
    """Le script installé passe par `main()` : sortie en UTF-8 même sur une console cp1252."""
    resultat = subprocess.run(
        [sys.executable, "-c", "from waveaudit.interfaces.cli import main; main()", "--help"],
        capture_output=True,
        env={"PYTHONIOENCODING": "cp1252", "SYSTEMROOT": os.environ["SYSTEMROOT"]},
        check=True,
    )
    assert "vulnérabilité".encode() in resultat.stdout
