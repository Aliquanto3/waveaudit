"""Tests des garde-fous du récit incident (contrats §21, CAP-5).

Décision d'orchestration (C1 -> C4) : les motifs normatifs de `domaine.incident` ratent un
jeton suivi d'un point final de phrase ; `garde_fous_incident` les applique sur une copie du
texte où ce point final devient une espace. Voir les reports de la story C1.
"""

import pytest

from tests.faux_moteur import REFERENCES_INVENTEES_INCIDENT
from tests.incident_outils import detection, regle
from waveaudit.domaine.garde_fous_incident import appliquer_recit
from waveaudit.domaine.incident import Indicateur
from waveaudit.domaine.modeles import CodeMotif, Motif, Statut


def _sortie(**surcharges) -> dict:
    donnees = {
        "titre": "Force brute SSH sur BASTION01",
        "recit": "Huit échecs d'authentification SSH depuis la même adresse en 70 secondes.",
        "impact": "Un attaquant peut deviner un mot de passe et ouvrir une session.",
        "recommandation": "Bloquer l'adresse source et imposer l'authentification par clé.",
    }
    return donnees | surcharges


def _detection_avec_indicateurs(**indicateurs_surcharges):
    d = detection()
    indicateurs = indicateurs_surcharges.get(
        "indicateurs",
        [Indicateur(type="ip", valeur="203.0.113.45", origines=["auth.log:1"])],
    )
    return d.model_copy(update={"indicateurs": indicateurs})


def test_nominal_sans_motif():
    recit = appliquer_recit(_sortie(), regle(), _detection_avec_indicateurs(), 800)
    assert recit.statut == Statut.OK
    assert recit.motifs == []
    assert recit.regle_titre == "Force brute SSH"
    assert recit.titre == "Force brute SSH sur BASTION01"


def test_technique_gardee_si_reference_exacte():
    recit = appliquer_recit(
        _sortie(recit="Correspond à la technique T1110.001 (ATT&CK)."),
        regle(),
        _detection_avec_indicateurs(),
        800,
    )
    assert "T1110.001" in recit.recit
    assert recit.motifs == []


def test_technique_retiree_si_sous_technique_differente():
    recit = appliquer_recit(
        _sortie(recit="Correspond à la technique T1110 (générique) ici même."),
        regle(),
        _detection_avec_indicateurs(),
        800,
    )
    assert "T1110" not in recit.recit
    assert recit.statut == Statut.A_REVOIR
    assert any(m.code == CodeMotif.REFERENCE_RETIREE and m.detail == "T1110" for m in recit.motifs)


def test_ip_et_hachage_presents_conserves_casse_differente_et_ipv4_mappee():
    indicateurs = [
        Indicateur(type="ip", valeur="203.0.113.45", origines=["auth.log:1"]),
        Indicateur(
            type="hachage",
            valeur="0f" * 32,
            origines=["sysmon.csv:1"],
        ),
    ]
    sortie = _sortie(
        recit=(
            "Adresse 203.0.113.45 et adresse mappée ::FFFF:203.0.113.45 "
            "vues avec le hachage " + ("0F" * 32) + " associé."
        )
    )
    recit = appliquer_recit(
        sortie, regle(), _detection_avec_indicateurs(indicateurs=indicateurs), 800
    )
    assert "203.0.113.45" in recit.recit
    assert ("0f" * 32) in recit.recit.lower()
    assert recit.motifs == []


def test_references_inventees_point_final_retirees():
    """Vecteur du faux moteur (contrats §21, revue C1) : technique, IPv4 et hachage inventés.

    `REFERENCES_INVENTEES_INCIDENT` se termine par une IP sans point final à l'intérieur,
    mais le texte complet se termine par un « . » de fin de phrase : les trois jetons
    doivent tous être retirés, y compris ceux collés à ce point final.
    """
    sortie = _sortie(recit=_sortie()["recit"] + REFERENCES_INVENTEES_INCIDENT + ".")
    recit = appliquer_recit(sortie, regle(), _detection_avec_indicateurs(), 800)
    retires = [m for m in recit.motifs if m.code == CodeMotif.REFERENCE_RETIREE]
    indicateur_retires = [m for m in recit.motifs if m.code == CodeMotif.INDICATEUR_RETIRE]
    assert len(retires) == 2
    assert {m.detail for m in retires} == {"T9999", "T1110.999"}
    assert len(indicateur_retires) == 2
    assert {m.detail.lower() for m in indicateur_retires} == {"203.0.113.254", "0f" * 32}
    assert "T9999" not in recit.recit
    assert "T1110.999" not in recit.recit
    assert "203.0.113.254" not in recit.recit
    assert ("0f" * 32) not in recit.recit.lower()


def test_technique_inventee_point_final_seule_retiree():
    sortie = _sortie(recit="Technique inventée T9999. Fin de la phrase ici même.")
    recit = appliquer_recit(sortie, regle(), _detection_avec_indicateurs(), 800)
    assert "T9999" not in recit.recit
    assert any(m.code == CodeMotif.REFERENCE_RETIREE and m.detail == "T9999" for m in recit.motifs)


def test_ipv4_inventee_point_final_retiree():
    sortie = _sortie(recit="Vu depuis 203.0.113.254. Rien d'autre à signaler ici.")
    recit = appliquer_recit(sortie, regle(), _detection_avec_indicateurs(), 800)
    assert "203.0.113.254" not in recit.recit
    assert any(
        m.code == CodeMotif.INDICATEUR_RETIRE and m.detail == "203.0.113.254" for m in recit.motifs
    )


def test_ipv6_inventee_point_final_retiree():
    sortie = _sortie(recit="Vu depuis 2001:db8::1. Rien d'autre à signaler ici.")
    recit = appliquer_recit(sortie, regle(), _detection_avec_indicateurs(), 800)
    assert "2001:db8::1" not in recit.recit
    assert any(m.code == CodeMotif.INDICATEUR_RETIRE for m in recit.motifs)


@pytest.mark.parametrize(
    ("fragment", "jeton", "code"),
    [
        ("Source (203.0.113.254.) vue", "203.0.113.254", CodeMotif.INDICATEUR_RETIRE),
        ("Vu 203.0.113.254., puis rien", "203.0.113.254", CodeMotif.INDICATEUR_RETIRE),
        ("Vu 203.0.113.254.; puis rien", "203.0.113.254", CodeMotif.INDICATEUR_RETIRE),
        ("Vu « 203.0.113.254. » cité", "203.0.113.254", CodeMotif.INDICATEUR_RETIRE),
        ('Vu "203.0.113.254." cité', "203.0.113.254", CodeMotif.INDICATEUR_RETIRE),
        ("Vu [203.0.113.254.] cité", "203.0.113.254", CodeMotif.INDICATEUR_RETIRE),
        ("Vu 203.0.113.254... puis", "203.0.113.254", CodeMotif.INDICATEUR_RETIRE),
        ("Vers 2001:db8::1.) fin", "2001:db8::1", CodeMotif.INDICATEUR_RETIRE),
        ("Voir (T1059.003.) ici", "T1059.003", CodeMotif.REFERENCE_RETIREE),
    ],
)
def test_jeton_invente_point_puis_ponctuation_retire(fragment, jeton, code):
    """Revue C4 : « . » suivi d'une ponctuation fermante ou séparatrice, pas d'un blanc."""
    sortie = _sortie(recit="Échecs répétés depuis une adresse externe. " + fragment)
    recit = appliquer_recit(sortie, regle(), _detection_avec_indicateurs(), 800)
    assert jeton not in recit.recit
    assert Motif(code=code, detail=jeton) in recit.motifs


def test_non_mutilation_point_puis_ponctuation():
    texte = (
        "Outil v2.4.1.) et (10.0.19045.), T1110.001, 08:02:10.; "
        "2026-10-14T08:02:10+02:00.) et (203.0.113.45.) ainsi que ::ffff:203.0.113.45."
    )
    recit = appliquer_recit(_sortie(recit=texte), regle(), _detection_avec_indicateurs(), 800)
    assert recit.recit == texte
    assert recit.motifs == []


def test_non_mutilation_horaire_iso_version_et_hexa():
    sortie = _sortie(
        recit=(
            "À 08:02:10 puis 2026-10-14T08:02:10+02:00, l'outil 10.0.17763.1 a émis le code 0x1010."
        )
    )
    recit = appliquer_recit(sortie, regle(), _detection_avec_indicateurs(), 800)
    assert "08:02:10" in recit.recit
    assert "2026-10-14T08:02:10+02:00" in recit.recit
    assert "10.0.17763.1" in recit.recit
    assert "0x1010" in recit.recit
    assert recit.motifs == []


def test_rubrique_sous_20_caracteres_completee():
    recit = appliquer_recit(_sortie(impact="Court."), regle(), _detection_avec_indicateurs(), 800)
    assert recit.impact == regle().impact
    assert any(
        m.code == CodeMotif.RUBRIQUE_COMPLETEE and m.detail == "impact" for m in recit.motifs
    )
    assert recit.statut == Statut.A_REVOIR


def test_titre_vide_recopie_titre_regle():
    recit = appliquer_recit(_sortie(titre=""), regle(), _detection_avec_indicateurs(), 800)
    assert recit.titre == regle().titre
    assert any(m.code == CodeMotif.RUBRIQUE_COMPLETEE and m.detail == "titre" for m in recit.motifs)


def test_regle_titre_toujours_recopie_meme_avec_garde_fous():
    recit = appliquer_recit(_sortie(titre=""), regle(), _detection_avec_indicateurs(), 800)
    assert recit.regle_titre == regle().titre


def test_repli_sortie_invalide():
    r = regle()
    sortie = {
        "titre": r.titre,
        "recit": r.description,
        "impact": r.impact,
        "recommandation": r.recommandation,
    }
    recit = appliquer_recit(
        sortie,
        r,
        _detection_avec_indicateurs(),
        800,
        motifs_initiaux=[Motif(code=CodeMotif.REPLI_SORTIE_INVALIDE, detail="sortie invalide")],
    )
    assert recit.statut == Statut.A_REVOIR
    assert any(m.code == CodeMotif.REPLI_SORTIE_INVALIDE for m in recit.motifs)
    assert recit.recit == r.description
    assert recit.impact == r.impact
    assert recit.recommandation == r.recommandation


def test_invariant_statut_motifs():
    recit_ok = appliquer_recit(_sortie(), regle(), _detection_avec_indicateurs(), 800)
    assert (recit_ok.statut == Statut.A_REVOIR) == bool(recit_ok.motifs)
    recit_ko = appliquer_recit(_sortie(impact=""), regle(), _detection_avec_indicateurs(), 800)
    assert (recit_ko.statut == Statut.A_REVOIR) == bool(recit_ko.motifs)
    assert recit_ko.statut == Statut.A_REVOIR
