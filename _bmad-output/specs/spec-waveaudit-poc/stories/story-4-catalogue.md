---
id: story-4
title: Catalogue de constats types
status: review
sources:
  - ../stories.yaml
  - ../../../planning-artifacts/architecture/architecture-waveaudit-2026-10-17/contrats.md
---

# Story 4 — Catalogue de constats types

## Livré

- `donnees/catalogue/{web,ad,infra,config,crypto,autre}.yaml` : 35 constats types figés par
  contrats §16 (16 web, 6 ad, 5 infra, 4 config, 3 crypto, 1 autre), rédigés en propre (aucune
  copie de CWE, OWASP ou ANSSI). Chaque constat porte 6 à 12 `mots_cles` FR/EN, au moins une
  référence de forme canonique (`CWE-n` ou `A0X:2021`) avec une URL `https://` réelle
  (`cwe.mitre.org`, `owasp.org`), un `cvss_vecteur` canonique et cohérent avec la description, et
  `source = "Rédaction WaveAudit d'après <références>, licence du dépôt"`.
- `src/waveaudit/adaptateurs/catalogue_yaml.py` :
  - `CatalogueYaml(dossier)` implémente le port `domaine.ports.Catalogue` (contrats §3) :
    `constats()` (triés par `id`, lève `ConfigurationInvalide` si un fichier est illisible, une
    entrée est invalide ou des `id` sont dupliqués) et `obtenir(id)` (lève `EntreeInvalide` si
    absent).
  - `verifier(dossier) -> list[str]` (utilisée plus tard par la CLI `catalogue verifier`,
    contrats §19) : contrôle indépendamment, par fichier `*.yaml` du dossier, le schéma
    `ConstatType`, l'unicité des `id`, le préfixe d'`id` cohérent avec la famille et le nom du
    fichier, la forme canonique du `cvss_vecteur` (évaluable et recanonisé via
    `domaine.cvss31`), la présence et la forme des références (`id` canonique, `url` en
    `https://`), la présence des 35 identifiants figés et un total d'au moins 30 constats.
    Renvoie une ligne par erreur (`fichier:id: message`), jamais ne lève d'exception pour un
    catalogue de test invalide.
- `tests/unitaires/test_catalogue.py` : le catalogue du dépôt passe `verifier` et se charge via
  `constats()` (35 entrées, ids uniques et triés) ; chacune des règles de `verifier` a un test
  d'échec dédié sous `tmp_path` ; `constats()`/`obtenir()` sont testés indépendamment de
  `verifier` (succès, doublon, identifiant absent).

## Écarts au contrat (variantes minimales)

- Signature publique `CatalogueYaml.constats()` / `.obtenir(id)` (port `Catalogue`, contrats §3)
  plutôt qu'un `charger()` ad hoc : l'`invoke_dev_with` de la story ne mentionnait pas cette
  méthode nommément, mais le port du socle (AD-0, `domaine/ports.py`) l'impose et n'est pas
  modifiable par cette story.
- `verifier` ne dépend pas de `CatalogueYaml.constats()` : elle relit et valide chaque fichier
  elle-même pour pouvoir continuer après un fichier illisible ou une entrée invalide et
  rapporter toutes les erreurs trouvées en une seule passe, plutôt que de s'arrêter à la
  première exception.
- Les références du catalogue réel n'utilisent que les formes `CWE-n` et `A0X:2021` (pas
  `CAPEC-n`, `WSTG-…`, `ANSSI-…` ni `CERTFR-…`) : ces formes restent acceptées par la regex de
  `verifier` et sont couvertes par les cas d'échec des tests, mais n'apparaissent pas dans les
  35 constats figés, pour limiter le risque de citer une URL ANSSI dont l'adresse exacte ne
  peut pas être vérifiée hors ligne.

## Reports

- Aucun.
