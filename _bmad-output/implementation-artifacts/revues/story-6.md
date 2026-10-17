# Revue story 6 — Adaptateur moteur compatible OpenAI

Branche `story-6-revue` (depuis `story-6` 4638e0c, à jour sur main). Contrat : contrats §3, AD-3.

## Revue

| Sévérité | Source | Constat | Décision | Motif |
|---|---|---|---|---|
| medium | second avis 1 | Réponse 200 malformée (corps non JSON, `choices` vide, `message` absent, `content` null) levait `JSONDecodeError`/`IndexError`/`KeyError`/`TypeError`. Seules les erreurs du domaine sont prévues (contrats §5, §6 : rien d'autre ne sort d'`executer_lot`) : le lot aurait planté. | Corrigé | `content` non textuel → `SortieInvalide` (le contenu n'est pas du JSON). Enveloppe non conforme → `MoteurInjoignable` (repli `repli_moteur`). Écart à consigner : le contrat ne classe pas l'enveloppe non conforme ; `MoteurInjoignable` garde « `SortieInvalide` seulement pour le contenu » au sens littéral. Tests paramétrés via `httpx.MockTransport`. |
| low | second avis 2 | Scénarios `json_invalide_une_fois`, `references_inventees`, `vecteur_invalide` non couverts. | Rejeté | Ils exercent le workflow (nouvel essai, garde-fous), pas l'adaptateur, qui ne valide pas le schéma (AD-3) ; à couvrir par les stories workflow. |
| low | second avis 3 | `base_url` non validée (`/v1`, `127.0.0.1`). | Rejeté | La règle AD-3 s'applique à la construction de la config (`application/config.py`) ; la garde réseau (story 7) couvre le hors-ligne. |
| low | second avis 4 | Client httpx jamais fermé. | Rejeté | `fermer()` existe ; aucun appelant encore : à appeler par la composition (`ouvrir_moteur`). |
| low | reviewer | Critère « sonder KO » couvert seulement par la connexion refusée, pas par un statut != 200. | Corrigé | Test ajouté : `/models` en 404. |
| low | reviewer | Tests d'`Authorization` sur les en-têtes du client, pas sur la requête reçue (le faux moteur n'enregistre pas les en-têtes). | Rejeté | httpx envoie les en-têtes par défaut du client ; preuve suffisante sans toucher au socle. |
| — | reviewer | Complexité : aucune structure qui grossit dans l'adaptateur. | — | 0 constat. |

Tests : `tests/unitaires/test_moteur_openai.py` 16 verts ; suite complète 122 verts ; ruff check et format verts.
Report : aucun (pas de service réel requis ; vérification sur llama-server réel au banc, hors nuit).
