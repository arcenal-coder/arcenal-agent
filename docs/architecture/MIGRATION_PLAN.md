# Plan de migration après le Lot 0

## Lot 0 — audit et stabilisation

- cartographie de l’existant ;
- contrat de thème unique et correction du Chat ;
- confirmation de la télémétrie LLM existante ;
- baseline, dette et tests de non-régression.

## Lot 1 — ARC Core et Agent Manager

- service d’orchestration interne ;
- registre versionné reliant agents métier et profils Hermes ;
- contrats `AgentRequest`, `AgentResponse`, `ContextPlan` et erreurs ;
- politiques par application, utilisateur et niveau d’autonomie ;
- tests sans exposer encore une API inter-application publique.

Critère de sortie : le Chat ARC passe par l’orchestrateur sans régression et un
profil spécialisé peut être sélectionné explicitement avec audit.

## Lot 2 — RAG central et Context Builder

- collections et ACL ;
- chunking déterministe et index lexical dédié ;
- embeddings configurables et index vectoriel reconstruisible ;
- recherche hybride, reranking, budgets et citations ;
- évaluation de pertinence et métriques de contexte.

## Lot 3 — LDA et wiki documentaire

- connecteur SilverBullet natif en lecture seule et synchronisation par `ETag` ;
- miroir Markdown reconstructible indexé par le RAG central ;
- extraction bornée des pièces jointes TXT, Markdown, DOCX, ODT et PDF ;
- métadonnées structurées et migrations réversibles ;
- traitement asynchrone des pièces jointes ;
- propositions d’amélioration, revue et notifications ;
- droits wiki et publication par groupes YunoHost ;
- export, audit et recette documentaire.

## Lot 4 — Enterprise Memory

- taxonomie des faits, décisions, personnes, projets et politiques ;
- provenance, durée de conservation, correction et oubli ;
- séparation conversation / entreprise / processus ;
- outils d’administration et consentement.

## Lot 5 — Agents spécialisés et API applications

- ARC Core, Agent Manager et Agent ATS livrés au lot 01 ;
- authentification inter-applications minimale par secret dédié livrée ;
- API `/api/v1/agents/{agent}/query` livrée et testée ;
- renforcer l'identité utilisateur signée avant RH, QSSE et les agents suivants ;
- idempotence, audit, budgets et tests contractuels.

## Lot 6 — ARC Frugal et Model Router

- routage selon difficulté, confidentialité, coût et disponibilité ;
- budgets par application/agent ;
- cache et réduction de contexte mesurés ;
- comparaison à `AI_BASELINE.md`.

## Lot 7 — Automatisation et Process Memory

- moteur de processus au-dessus du cron actuel ;
- étapes reprenables, approbations et preuves ;
- mémoire d’exécution structurée ;
- notifications et escalades.

## Lot 8 — durcissement système

- revue croisée du paquet `arcenal_ynh` ;
- rotation d’identités, sauvegarde/restauration et reprise après incident ;
- réduction des privilèges et tests de pénétration ;
- recette YunoHost stock, mise à niveau et retour arrière.

## Règles transverses

- conserver Hermes synchronisable en privilégiant les points d’extension ;
- une migration de données doit être sauvegardable, rejouable et réversible ;
- aucune capacité root libre ;
- chaque lot ajoute tests, mesures et documentation avant promotion stable ;
- ne jamais confondre index dérivé et source documentaire canonique.
