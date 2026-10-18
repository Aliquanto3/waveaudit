# Prompt de cadrage de la version 2 (à lancer après `/clear`)

```
Session de CADRAGE de la version 2 de WaveAudit, sans écrire de code.
Nous sommes sur l'EliteBook cible : les mesures de la nuit valent pour la cible.

0. Version 0.1.0 d'abord. Le POC est livré, testé et mesuré sur la cible.
   Propose-moi la release v0.1.0 et attends mon accord avant de la faire :
   version dans pyproject, tag annoté, release GitHub avec notes tirées de
   etat-de-nuit.md, topic `status-test`.

1. Lis seulement ces fichiers (en confiant les gros à agent-cost-kit:lookup) :
   - _bmad-output/implementation-artifacts/etat-de-nuit.md : bilan et
     « Écarts à arbitrer » ;
   - _bmad-output/implementation-artifacts/bilan-modeles.md et
     validation-moteur.md : qualité des fiches, recopie, rattachement, modèles ;
   - les « Non-goals » et reports de _bmad-output/specs/spec-waveaudit-poc/SPEC.md
     et de _bmad-output/specs/spec-waveaudit-cert/SPEC.md ;
   - les décisions verrouillées et les idées pour plus tard de
     _bmad-output/forge/slm-edge-consultants-cyber/forged-idea.md ;
   - _bmad-output/planning-artifacts/architecture/architecture-waveaudit-2026-10-17/
     (ARCHITECTURE-SPINE.md, contrats.md), pour savoir ce que chaque choix
     touche.

2. Fais-moi arbitrer, en une liste courte avec une recommandation pour
   chaque point (un passage par AskUserQuestion, pas une question par point) :
   a. les écarts à entériner dans contrats.md : `reflexion` (§22),
      neutralisation du point final (§21), nouvelle tentative avec une seed
      fixe et `</note>` non échappé (§5 et §8), seuil de 20 caractères pour
      les titres (§6), pic RSS (§20), nom d'hôte [::1] (§18), noms privés de
      lot.py, et les autres points de la liste ;
   b. les fonctionnalités mises de côté à faire entrer dans la v2 :
      relecture et édition des fiches dans l'UI (choisir un autre des
      3 constats candidats, corriger le texte, valider puis exporter),
      workflow incident dans l'UI, choix du modèle dans l'UI, fiches en
      anglais, import Burp et Nessus, EVTX côté CERT, autres workflows du
      backlog (scripts, défense) ;
   c. les chantiers de qualité qui précèdent l'UI : rattachement (notes 01
      et 29 du banc), recopie du catalogue (0,93), choix du modèle par
      défaut (granite ou qwen3-1.7b), `repeat_penalty`, langue des récits
      MiniCPM5.
   Dis-moi lesquelles de ces décisions rouvrent une décision verrouillée du
   cadrage. Un changement de cap global passe par `bmad-correct-course`.

3. Cadrage UX avec `bmad-ux`, si la relecture des fiches entre dans la v2 :
   DESIGN.md et EXPERIENCE.md sous _bmad-output/planning-artifacts/ux/.
   Parcours du consultant : déposer, suivre, relire chaque fiche à côté de
   sa note, corriger, valider, exporter. Plus l'incident côté CERT s'il est
   retenu. Contraintes : 127.0.0.1 seulement, aucune ressource externe
   (CDN, polices), pas de charte Wavestone (theme-prive/), bandeau
   démonstration, accessibilité de base, Windows sans droits admin.

4. Spec v2 avec `bmad-spec`, dans _bmad-output/specs/spec-waveaudit-v2/
   (SPEC.md, formats.md si besoin, stories.yaml). Puis mise à jour de
   l'architecture avec `bmad-architecture` : amender contrats.md pour les
   écarts entérinés et les nouveaux contrats (API de l'UI, persistance des
   corrections, format d'export). Chaque story porte `description` et
   `invoke_dev_with`, et nomme les fichiers et les tests existants à
   réaligner.

5. Relecture adversariale de la spec avant tout code. Elle est obligatoire,
   car il s'agit d'une refonte d'interface et que la sécurité de l'UI locale
   est en jeu : `bmad-review` sur SPEC, contrats et stories, puis
   intégration des constats.

6. Plan d'exécution sur le modèle de
   _bmad-output/implementation-artifacts/plan-de-nuit.md : vagues,
   parallélisation à faible risque, suite complète après les vagues
   sensibles, règles d'arrêt. Écris-le dans plan-v2.md, avec etat-v2.md.
   Puis ARRÊTE-TOI : l'exécution se fera dans une autre session, après
   `/clear`.

Règles : celles de CLAUDE.md (session principale qui orchestre, pas de
code, contexte court). Commits en français, poussés sur main après mon
accord à la fin de chaque étape.
```
