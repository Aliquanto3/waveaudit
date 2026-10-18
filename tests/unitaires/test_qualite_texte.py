"""Tests de `domaine/qualite_texte.py` (contrats §6 v2 étapes 5 et 6, §21 v2)."""

from waveaudit.adaptateurs.catalogue_yaml import CatalogueYaml
from waveaudit.application.config import racine_projet
from waveaudit.domaine.qualite_texte import est_repetitif, motif_langue

RACINE = racine_projet()


# --- est_repetitif (étape 5) -----------------------------------------------------------------


def test_trigrammes_sous_le_seuil_non_repetitif():
    """9 trigrammes, tous distincts : sous `_TRIGRAMMES_MIN`, jamais signalé par ce critère."""
    texte = "un deux trois quatre cinq six sept huit neuf dix onze"
    assert est_repetitif(texte) is False


def test_trigrammes_ratio_030_atteint_repetitif():
    """20 mots, motif de 3 mots répété 6 fois (12 mots) puis 8 mots distincts : ratio >= 0.30."""
    bloc = "alpha beta gamma " * 6
    texte = bloc + "un deux trois quatre cinq six sept huit"
    assert est_repetitif(texte) is True


def test_trigrammes_ratio_juste_sous_030_non_repetitif():
    texte = "alpha beta gamma " * 2 + " ".join(f"mot{i}" for i in range(14))
    assert est_repetitif(texte) is False


def test_boucle_sans_espace_quarante_caracteres_repetitive():
    texte = "Préambule. " + ("abcde" * 10) + " Fin de phrase."
    assert est_repetitif(texte) is True


def test_boucle_sous_quarante_caracteres_non_retenue():
    texte = "Préambule. " + ("ab" * 10) + " Fin de phrase courte."
    assert est_repetitif(texte) is False


def test_boucle_sans_lettre_non_retenue():
    texte = "Préambule. " + ("123456" * 10) + " Fin de phrase."
    assert est_repetitif(texte) is False


_DEBUT_RECIT = (
    "Le consultant a observé durant le test une séquence encodée particulière relevée "
    "dans les journaux du serveur web lors de l'audit mené hier après-midi sur le portail "
)
_FIN_RECIT = (
    "client avant la publication du rapport final aux équipes concernées et au comité de "
    "pilotage interne chargé du suivi des correctifs appliqués ensuite par les équipes "
    "techniques en charge de la remédiation complète du système exposé publiquement sur "
    "internet et accessible depuis plusieurs zones réseau distinctes identifiées au préalable "
    "ainsi que dans le registre des incidents clôturé par le responsable de la sécurité."
)


def test_charges_citees_sans_repetition():
    """Revue A19/E37 : une charge citée telle quelle depuis la source n'est pas une boucle."""
    for charge in ("../" * 15, "A" * 45, "%2e" * 15):
        texte = _DEBUT_RECIT + charge + " " + _FIN_RECIT
        source = f"Capture réseau : {charge} observée telle quelle."
        assert est_repetitif(texte, source) is False


def test_charge_non_citee_reste_detectee_comme_boucle():
    """Sans citation, une charge de 40+ caractères avec une lettre reste une boucle."""
    charge = "A" * 45
    texte = _DEBUT_RECIT + charge + " " + _FIN_RECIT
    assert est_repetitif(texte, "") is True


# --- motif_langue : écriture --------------------------------------------------------------


def test_ecriture_non_latine_signalee():
    assert motif_langue("Un caractère étranger ici : 経.", "fr") == "écriture non latine"


def test_lettres_modificatrices_et_ordinaux_tolerees():
    """Revue E35/E36 : `Lm` (ʼ, ˆ) et les ordinaux (º, ª, µ) ne déclenchent jamais le motif."""
    texte = "Le nº de ticket et la tournure à la ʼbonneˆ n'ont rien d'anormal. µ toléré aussi."
    assert motif_langue(texte, "fr") is None


def test_non_latin_cite_depuis_la_note():
    """Revue E35/E36 : une lettre non latine présente dans la note (citation) est ignorée."""
    source = "Le journal affiche текст суровый tel quel."
    texte = "Le journal affiche текст суровый dans la capture d'écran jointe au constat."
    assert motif_langue(texte, "fr", source) is None
    assert motif_langue(texte, "fr", "") == "écriture non latine"


def test_non_latin_cite_avec_ponctuation_collee():
    """Revue Q2 : la citation est reconnue par lettre, ponctuation collée comprise."""
    source = "Le champ contient Жертва."
    assert motif_langue("Le module accepte Жертва, puis la valeur.", "fr", source) is None
    assert motif_langue("Le module accepte Жертва, puis 経.", "fr", source) == (
        "écriture non latine"
    )


# --- motif_langue : mots-outils ------------------------------------------------------------


def test_mots_outils_anglais_dans_texte_francais_signale():
    texte = (
        "The application does not validate the input that is sent by the user, and this "
        "allows an attacker to inject content into the page."
    )
    assert motif_langue(texte, "fr") == "mots-outils en"


def test_mots_outils_francais_dans_texte_anglais_signale():
    texte = (
        "L'application ne valide pas les données envoyées par l'utilisateur, ce qui permet à "
        "un attaquant d'injecter du contenu dans la page."
    )
    assert motif_langue(texte, "en") == "mots-outils fr"


def test_3des_et_sigles_sans_motif():
    """Revue E32-E34 : `3DES` (mot collé à un chiffre) et les sigles tout capitales ignorés."""
    texte = "Le chiffrement 3DES reste actif sur ce DES IT TO legacy, sans mot-outil français ici."
    assert motif_langue(texte, "fr") is None


def test_citation_anglaise_dans_rubrique_francaise():
    """Revue E32-E34 : un segment cité entre guillemets n'est pas compté."""
    texte = (
        "Le journal affiche le message « The user is not allowed to log in » dans la console "
        "sans autre remarque notable."
    )
    assert motif_langue(texte, "fr") is None


def test_titre_jamais_soumis_aux_mots_outils():
    titre_anglais = (
        "The application does not validate the input that is sent by the user and this "
        "allows an attack."
    )
    assert motif_langue(titre_anglais, "fr") == "mots-outils en"
    assert motif_langue(titre_anglais, "fr", verifier_mots_outils=False) is None


def test_aucun_faux_positif_sur_les_textes_francais_du_catalogue():
    """Mesure du contrat (2026-10-18) : 0 mot-outil anglais dans les textes fr du catalogue."""
    constats = CatalogueYaml(RACINE / "donnees" / "catalogue").constats()
    for constat in constats:
        for champ in ("description", "impact", "recommandation"):
            texte = getattr(constat, champ)
            assert motif_langue(texte, "fr") is None, f"{constat.id}.{champ}"
            assert est_repetitif(texte) is False, f"{constat.id}.{champ}"
