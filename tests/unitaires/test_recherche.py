"""Tests de `domaine/recherche.py` (BM25, contrats §7)."""

from waveaudit.domaine.modeles import ConstatType, Note, Reference
from waveaudit.domaine.recherche import classer, requete_depuis_note

_REF = Reference(id="r1", titre="Référence", url="https://example.invalid/r1")


def _constat(
    id_: str, titre: str, mots_cles: list[str], description: str = "description générique"
) -> ConstatType:
    return ConstatType(
        id=id_,
        titre=titre,
        famille="web",
        mots_cles=mots_cles,
        description=description,
        impact="impact",
        recommandation="recommandation",
        cvss_vecteur="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N",
        references=[_REF],
        source="source interne",
    )


def test_tokenisation_accents_casse_mots_vides() -> None:
    catalogue = [
        _constat("c1", "Mot de passe par défaut", ["authentification"]),
        _constat("c2", "Chiffrement faible", ["crypto"]),
    ]
    # "MOT DE PASSE" en majuscules et sans accent doit matcher "mot de passe par défaut"
    # malgré les mots vides ("de", "par") et la casse.
    candidats = classer(catalogue, "MOT DE PASSE", k1=1.5, b=0.75)
    scores = {c.id: c.score for c in candidats}
    assert scores["c1"] > 0.0
    assert scores["c1"] > scores["c2"]


def test_ponderation_par_repetition() -> None:
    # c1 répète le mot-clé de la requête dans son titre ET ses mots-clés : il doit
    # dominer c2 qui ne le porte qu'une fois dans sa description.
    catalogue = [
        _constat("c1", "Injection SQL", ["injection", "sql"], "faille d'injection"),
        _constat("c2", "Anomalie réseau", ["réseau"], "mentionne une injection en passant"),
    ]
    candidats = classer(catalogue, "injection sql", k1=1.5, b=0.75)
    scores = {c.id: c.score for c in candidats}
    assert scores["c1"] > scores["c2"] > 0.0


def test_idf_toujours_positif_meme_terme_present_partout() -> None:
    catalogue = [
        _constat("c1", "Constat réseau", ["réseau"]),
        _constat("c2", "Autre constat réseau", ["réseau"]),
        _constat("c3", "Encore un constat réseau", ["réseau"]),
    ]
    # "réseau" est présent dans tous les documents (n == N) : l'IDF classique
    # deviendrait négatif ou nul, la variante BM25 (ln(1 + ...)) reste positive.
    candidats = classer(catalogue, "réseau", k1=1.5, b=0.75)
    for candidat in candidats:
        assert candidat.score > 0.0


def test_egalite_departagee_par_id() -> None:
    catalogue = [
        _constat("b", "Même contenu", ["pareil"]),
        _constat("a", "Même contenu", ["pareil"]),
    ]
    candidats = classer(catalogue, "même contenu pareil", k1=1.5, b=0.75)
    assert [c.score for c in candidats] == [candidats[0].score] * 2
    assert [c.id for c in candidats] == ["a", "b"]


def test_requete_sans_jeton_connu_scores_zero() -> None:
    catalogue = [
        _constat("c1", "Mot de passe", ["authentification"]),
        _constat("c2", "Chiffrement faible", ["crypto"]),
    ]
    candidats = classer(catalogue, "zzqqxxjj inexistant", k1=1.5, b=0.75)
    assert all(c.score == 0.0 for c in candidats)


def test_classer_renvoie_tous_les_constats_meme_catalogue_vide() -> None:
    assert classer([], "quoi que ce soit", k1=1.5, b=0.75) == []


def test_requete_depuis_note_ignore_constat_attendu_et_actif() -> None:
    note = Note(
        fichier="n1.txt",
        titre="Titre de la note",
        actif="serveur-x",
        severite_pressentie="elevee",
        constat_attendu="ne doit jamais apparaître",
        corps="corps de la note",
    )
    assert requete_depuis_note(note) == "Titre de la note\ncorps de la note"
    assert "jamais" not in requete_depuis_note(note)
    assert "serveur-x" not in requete_depuis_note(note)
