"""Hiérarchie des erreurs de WaveAudit (contrats §4). Aucune n'hérite d'OSError."""


class ErreurWaveAudit(Exception):
    """Racine de toutes les erreurs métier de WaveAudit."""


class EntreeInvalide(ErreurWaveAudit):
    """Entrée absente ou mal formée (dossier de notes, vecteur, identifiant inconnu). Code 2."""


class ConfigurationInvalide(ErreurWaveAudit):
    """Configuration ou catalogue illisible ou non conforme. Code 2."""


class MoteurInjoignable(ErreurWaveAudit):
    """Connexion refusée, délai dépassé ou statut HTTP différent de 200. Code 3."""


class SortieInvalide(ErreurWaveAudit):
    """Contenu renvoyé par le moteur qui n'est pas un objet JSON."""


class ConnexionInterdite(ErreurWaveAudit):
    """Connexion réseau hors des hôtes autorisés pendant l'exécution. Code 4."""


class EmpreinteInvalide(ErreurWaveAudit):
    """Taille ou SHA-256 d'un artefact téléchargé différent du manifeste. Code 5."""
