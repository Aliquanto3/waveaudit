# Idée forgée : assistant d'audit local pour consultants cyber

**Issue : HARDENED** (2026-10-17)

## Contexte établi
- Utilisateurs : consultants du pool audit cyber de Wavestone. Un seul PC (16 Go, sans GPU), connecté au SI Wavestone (mail, VPN).
- Interdiction : politique liée à PASSI et aux contrats (périmètre maîtrisé), pas une coupure réseau. Un LLM interne Wavestone cloisonné reste possible à terme.
- Perf de référence : EliteBook i5-1145G7, 16 Go, CPU seul : 1,3 tok/s en chat, 5,7 tok/s en labo (`wavelocalai/docs/audits/`).

## Décisions verrouillées
1. **Produit = application d'assistance à l'audit au moteur interchangeable.** Endpoint compatible OpenAI : SLM local maintenant, LLM interne plus tard. La valeur durable est dans les workflows, le gabarit, le catalogue et le RAG.
2. **Fine-tuning = R&D personnelle séparée**, hors chemin critique.
3. **Filtre** : uniquement les tâches portant sur des données client. Les tâches génériques (formules, syntaxe) sont exclues.
4. **Cas n°1 : fiches de vulnérabilité.** On retrouve le constat type dans un catalogue, puis on l'adapte aux notes brutes. Pas de génération ex nihilo. Traitement par lot, pas en chat. **Cas n°2 : code** (scripts d'analyse des sorties d'outils).
5. **Séquence** : POC sur gabarit générique et données publiques → entrants des collègues et sponsor → pilote réel.
6. **Règles du POC** : vérifiablement hors ligne (test d'absence d'appel sortant, SBOM, SHA-256 des poids, source documentée) ; données publiques ou synthétiques seulement (CWE, OWASP WSTG, ANSSI ; notes fictives ; bandeau « démonstration ») ; périmètre figé : notes → fiche, FR, sortie Word.
7. **Distribution** : dépôt GitHub + `uv sync` (simple et auditable). Charte visuelle Wavestone ; format de fiche générique : Description / Impact / Recommandation / CVSS 3.1 / Références.
8. **Extension n°2 : CERT / réponse à incident**, prévue dans l'architecture (parseurs de logs, gabarit de rapport d'incident), non développée. DR/défense en backlog.

## Critères de réussite du POC
| Axe | Seuil |
|---|---|
| Qualité | ≥ 70 % de fiches utilisables après retouches légères (20 notes fictives, 2-3 collègues) |
| Fiabilité | 0 référence inventée (test déterministe sur le catalogue) |
| Vitesse | < 3 min par fiche, EliteBook 16 Go, Office ouvert |
| Mémoire | pic ≤ 6 Go |
| Installation | < 10 min |
| Hors ligne | aucun appel sortant (test automatisé) |
| Effet | ≥ 3 testeurs avec un entrant chacun, 1 sponsor identifié |

## Rejeté
- Assistant bureautique générique (mail, PPT, Excel) : contournement existant, et Copilot ou un LLM interne le rendra caduc.
- Chat interactif : rédhibitoire à 1,3-5 tok/s.
- SLM fine-tuné comme cœur du produit : coûteux, et périssable dès qu'un LLM interne arrive.
- Génération d'exploits : refus des SLM alignés ; les modèles « abliterated » posent un risque de supply chain.

## Points ouverts
- Entretien avec les collègues : (1) la frontière exacte (PASSI interne ou poste seul) ; (2) le poids réel des fiches dans une mission ; (3) la chaîne de rédaction et l'existence d'un catalogue de constats.
- Accès à PyPI, GitHub et Hugging Face depuis le poste ; variante archive des poids avec SHA-256.
- Moteur Windows sans compilateur : roue CPU précompilée ou `llama-server` épinglé.
- Charte Wavestone dans un dépôt public : accord de la communication, ou dépôt privé / thème hors dépôt.
- Risque de dispersion (6 dépôts actifs) : périmètre et date figés.
- Réutiliser : `service-public-slm-fine-tuning` (hors ligne, RAG, mesures CPU), `slm-quality-bench` (méthode de choix du modèle), `wavelocalai` (profil machine).
