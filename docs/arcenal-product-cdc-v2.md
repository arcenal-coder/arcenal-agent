# Cahier des charges détaillé — ARCenal Agent

Version : **2.0 approuvée**

Date de référence : 28 septembre 2026

Preuve de mandat : exigences détaillées fournies par l'utilisateur, puis
confirmées comme référence du produit lors du constat d'écart avec la version
installée. Ce document complète le résumé fonctionnel 1.1 sans en réduire le
périmètre.

## 1. Mission du produit

ARCenal Agent est une application native YunoHost. Son agent principal, ARC,
est l'architecte d'ARCenal Système : il observe, explique, configure, maintient
et répare le serveur dans un cadre contrôlé. Hermes reste le moteur technique
amont et n'apparaît que sous la mention discrète « by Hermes ».

La surcouche ARCenal reste périphérique au cœur Hermes afin de permettre des
mises à jour amont rapides. Les extensions, profils, compétences et API
spécifiques sont préférés aux modifications du cœur commun.

## 2. Principes de sécurité

- Le modèle IA n'est jamais root et ne connaît aucun mot de passe root.
- Toute opération privilégiée est une action structurée appartenant à un
  catalogue fermé ; aucune commande libre issue d'une conversation n'est
  exécutée avec des privilèges.
- Le chemin d'exécution est : utilisateur, ARC, permissions, risque,
  confirmation éventuelle, broker privilégié, résultat, vérification, audit.
- Les secrets restent dans le stockage privé et ne sont affichés ni dans les
  conversations, ni dans Markdown, Git, les journaux ou les erreurs.
- Les administrateurs ARC sont des administrateurs YunoHost existants. ARC ne
  crée pas de second mot de passe d'administration.

### Niveaux d'autorisation

1. Niveau 0 — lecture : observation, diagnostic et rapports sans confirmation.
2. Niveau 1 — action courante : action faible risque, bornée et réversible.
3. Niveau 2 — administration : changement de configuration ou d'application,
   avec confirmation selon la politique.
4. Niveau 3 — critique : suppression, réseau, SSH, pare-feu, stockage ou
   permissions système, avec confirmation humaine renforcée obligatoire.

Chaque confirmation présente l'action, la cible, le motif, la conséquence, le
risque, la possibilité de retour arrière et, en mode avancé, l'opération prévue.

## 3. Installation et premier démarrage

Le paquet YunoHost doit :

1. détecter et vérifier la version de YunoHost ;
2. sélectionner un administrateur YunoHost existant comme propriétaire ;
3. initialiser les identités séparées du moteur, du contrôle et du broker ;
4. détecter le serveur, le domaine et les informations système ;
5. créer les espaces privés de configuration, contexte, mémoire et directives ;
6. permettre la configuration d'un premier fournisseur IA ;
7. définir une identité de notification ARC sur un domaine configurable ;
8. présenter les permissions disponibles ;
9. terminer par un diagnostic d'installation ;
10. conserver toutes les données lors des mises à jour.

## 4. Interface principale

La navigation principale comporte exactement trois volets :

### ARC

Chat web natif, non terminal, permettant de diagnostiquer, expliquer,
superviser, maintenir et configurer le serveur. ARC cite les observations
réelles, propose un plan, sollicite les confirmations requises et vérifie le
résultat. L'historique peut être archivé ou supprimé.

### Agents

Création et administration d'agents spécialisés. Chaque agent possède une
identité, une mission, un fournisseur, un modèle principal et secondaire, des
compétences, des outils autorisés et une mémoire isolée. Les connecteurs ne
sont pas activés dans cette version ; leur futur contrat est AACP/1.

### RAG & LDA

Coffre documentaire Markdown portable inspiré du parcours Obsidian :

- arborescence, recherche plein texte, tags, aperçu et édition ;
- liens `[[Wiki]]`, liens entrants et historique des versions ;
- dépôt de PDF, DOCX, ODT, TXT et Markdown avec conservation de l'original ;
- recherche par ARC avec titre, référence, version et statut cités ;
- registre LDA calculé depuis les seules versions `Applicable` ;
- wiki salarié en lecture issu de la même publication ;
- export CSV et filtres métier QSSERP.

Le cycle est : `Brouillon`, `En révision`, `À approuver`, `Applicable`,
`Archivé`. ARC peut préparer une révision, mais ne publie jamais seul une
version applicable.

## 5. Centre Paramètres

Paramètres est un accès secondaire, distinct des trois volets métier. Sa
navigation interne contient onze sections extensibles.

### Général

Nom de l'agent et de l'organisation, langue, fuseau horaire, versions ARC,
Hermes, YunoHost et Debian, serveur, domaine principal et identité de
notification. Les données détectables ne sont pas redemandées.

### Apparence

Thèmes clair, sombre et système, couleurs dominantes, boutons, liens et texte,
logo, favicon et nom affiché, avec prévisualisation. Le thème utilise des
variables centralisées et récupère par défaut la personnalisation YunoHost.

### Contexte

Éditeur et aperçu de `CONTEXT.md`, avec sauvegarde, auteur, date, historique et
restauration. Son contenu décrit l'organisation, ses activités, équipes,
produits, implantations, vocabulaire, projets et architecture. Seuls les
éléments pertinents sont récupérés pour une requête LLM.

### Mémoire

Consultation, recherche, ajout, modification, suppression, historique et
restauration de `MEMORY.md`. La mémoire conserve décisions, préférences,
conventions, projets et actions entre les sessions. Les changements sensibles
respectent la politique de validation.

### Directives

Gestion explicite des fichiers `AGENTS.md`, `RULES.md`, `SECURITY.md` et
`TOOLS.md` ou de leurs équivalents existants : rôle, chemin, statut, auteur,
date, contenu, édition, historique et restauration. Une conversation ne peut
pas contourner les directives de sécurité.

### Fournisseurs IA

Adaptateurs pour OpenAI, Anthropic, Mistral, OpenRouter, Gemini, Ollama, les API
compatibles OpenAI, les fournisseurs internes et les extensions futures. Chaque
connexion gère URL, secret, modèles, modèles principal et secondaire,
activation, paramètres et test de connexion sans réafficher le secret.

### Accès

Comptes et API pour GitHub, Nextcloud, Dolibarr, messagerie, calendrier,
stockage, applications YunoHost et services métier. Chaque accès possède nom,
type, adresse, authentification, permissions, autonomie, état, dernier test,
bouton de test et désactivation.

### Outils et capacités

Inventaire des outils disponibles avec nom, description, origine, statut,
permissions, risque, confirmation, dernière utilisation et activation lorsque
possible. Les capacités héritées de Hermes et celles d'ARC sont distinguées.

### Système

Vue native de l'état général, versions, CPU, mémoire, stockage, charge,
services, applications, mises à jour, domaines, certificats, sauvegardes,
erreurs et alertes. Ces données alimentent directement les diagnostics du chat.

### Sécurité

Centre présentant administrateurs, utilisateurs, rôles, permissions, sessions,
connexions, fournisseurs, outils privilégiés, actions sensibles,
confirmations et événements. L'audit chaîné conserve utilisateur, origine,
action demandée et exécutée, cible, privilège, confirmation et résultat sans
secret.

### Sauvegardes

Pilotage et état des sauvegardes YunoHost d'ARC. La configuration, le contexte,
la mémoire, les directives, les paramètres, les fournisseurs, les métadonnées
d'accès, les outils et l'audit sont sauvegardés. Une restauration reconstruit
une instance exploitable et préserve les secrets par un mécanisme adapté.

## 6. Passerelle privilégiée et administration YunoHost

Le broker est séparé du processus LLM. Chaque action possède identifiant,
description, schéma de paramètres, autorisation, risque, confirmation,
exécution, vérification et retour arrière lorsque possible.

ARC doit pouvoir suivre un parcours complet tel que : identifier une
application défaillante, vérifier ses services et journaux, expliquer la cause,
proposer une correction, demander l'autorisation, exécuter et vérifier.

Le catalogue doit couvrir progressivement les usages administratifs YunoHost :
diagnostics, services, applications, utilisateurs, mises à jour, domaines,
certificats et sauvegardes. Toute action inconnue est refusée par défaut.

## 7. Extensibilité et maintien du fork

Les frontières interface, agent, fournisseurs, contexte, mémoire, directives,
accès, outils, permissions, risque, broker, YunoHost, secrets et audit restent
séparées. Les mécanismes Hermes existants sont réutilisés lorsqu'ils respectent
le besoin. Aucun écran ne présente une fonction simulée ou non raccordée.

## 8. Critères d'acceptation

- `AC-ARC-01` : l'arrivée ouvre le chat ARC, jamais le pilotage ou le terminal Hermes.
- `AC-ARC-02` : le chat répond via le fournisseur choisi, gère les erreurs et conserve l'historique.
- `AC-ARC-03` : ARC diagnostique une panne YunoHost avec faits, proposition, autorisation et vérification.
- `AC-AGT-01` : un agent complet peut être créé et persiste dans un profil isolé.
- `AC-AGT-02` : son identité, sa mission, ses modèles, compétences, outils et mémoire sont administrables depuis le volet Agents.
- `AC-RAG-01` : un document peut être créé, déposé, lu, modifié, relié et recherché.
- `AC-RAG-02` : seules les versions applicables alimentent automatiquement LDA et wiki.
- `AC-RAG-03` : ARC restitue une source traçable avec référence, version et statut.
- `AC-SET-01` : les onze sections Paramètres sont fonctionnelles et persistantes.
- `AC-AI-01` : plusieurs fournisseurs peuvent être enregistrés, testés et sélectionnés sans exposer leurs secrets.
- `AC-ACC-01` : chaque accès métier peut être testé, limité, désactivé et audité.
- `AC-SEC-01` : les quatre niveaux d'autorisation sont appliqués indépendamment du LLM.
- `AC-SEC-02` : une action critique exige une confirmation à usage unique et apparaît dans l'audit.
- `AC-YH-01` : ARC expose les informations système promises et peut les exploiter dans le chat.
- `AC-BKP-01` : installation, mise à jour, sauvegarde et restauration préservent un système exploitable et ses données.
- `AC-UX-01` : seules les trois entrées ARC, Agents et RAG & LDA sont principales ; Paramètres reste secondaire.
- `AC-UP-01` : la surcouche ARC reste isolée afin d'intégrer rapidement une nouvelle version Hermes.

Une fonction n'est terminée que si son backend réel, son interface, ses erreurs,
ses permissions, sa persistance, sa sécurité, ses tests et sa documentation sont
validés. Un écran visible ou un test unitaire isolé ne suffit pas.
