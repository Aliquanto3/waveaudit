"""Comportement de `static/relecture.js` (revue W3b) sous Node, s'il est installé.

Aucune dépendance ajoutée : sans `node` sur le PATH (CI), le test est sauté. Le harnais
(`tests/js/harnais_relecture.js`) simule le DOM, les minuteries et un faux serveur W3a :
file d'enregistrement par entrée, réessais, conflit, validation, candidat, export, dialogues.
L'aperçu CVSS est comparé au domaine (`cvss31.evaluer`) sur les 2592 vecteurs de base.
"""

import itertools
import json
import shutil
import subprocess

import pytest

from waveaudit.application.config import racine_projet
from waveaudit.domaine.cvss31 import evaluer

_RACINE = racine_projet()
_LIBELLES = {
    "aucune": "Aucune",
    "faible": "Faible",
    "moyenne": "Moyenne",
    "elevee": "Élevée",
    "critique": "Critique",
}


def test_relecture_js_sous_node(tmp_path):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node absent : harnais JS non lancé (REC dans un vrai navigateur)")
    attendus = []
    for av, ac, pr, ui, s, c, i, a in itertools.product(
        "NALP", "LH", "NLH", "NR", "UC", "NLH", "NLH", "NLH"
    ):
        vecteur = f"CVSS:3.1/AV:{av}/AC:{ac}/PR:{pr}/UI:{ui}/S:{s}/C:{c}/I:{i}/A:{a}"
        cvss = evaluer(vecteur)
        attendus.append([vecteur, f"{cvss.score:.1f} {_LIBELLES[cvss.severite]}"])
    fichier = tmp_path / "cvss_attendus.json"
    fichier.write_text(json.dumps(attendus, ensure_ascii=False), encoding="utf-8")
    resultat = subprocess.run(
        [
            node,
            str(_RACINE / "tests" / "js" / "harnais_relecture.js"),
            str(_RACINE / "src" / "waveaudit" / "interfaces" / "web" / "static" / "relecture.js"),
            str(fichier),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        check=False,
    )
    assert resultat.returncode == 0, resultat.stdout + resultat.stderr
    assert "tout vert" in resultat.stdout
