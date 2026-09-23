# Architecture du RAG, de la LDA et du wiki documentaire

Statut : **orientation fonctionnelle validée, réalisation à planifier**  
Date : 23 septembre 2026

## 1. Objectif

Le troisième volet d'ARC doit fournir une base de connaissances ouverte qui
réunit :

- la mémoire documentaire interrogeable par ARC ;
- la Liste des Documents Applicables (LDA) du système de management QSSERP ;
- un wiki consultable par les salariés autorisés ;
- le cycle d'amélioration continue des documents.

Cette base remplace l'idée d'une dépendance à Obsidian. Les connaissances
restent portables et exploitables sans l'interface choisie.

## 2. Principes structurants

1. Le Markdown et les métadonnées structurées constituent le format canonique.
2. Le wiki est une interface de consultation et d'édition, pas le propriétaire
   exclusif des données.
3. La LDA est une vue calculée des versions dont le statut est `Applicable`.
4. Une révision ne remplace jamais une version applicable avant son
   approbation.
5. ARC n'injecte pas tout le corpus dans le modèle : il recherche puis fournit
   uniquement les passages pertinents.
6. Les droits du wiki et du RAG respectent les groupes et permissions de
   YunoHost.
7. Chaque réponse fondée sur le RAG doit pouvoir citer les documents et leurs
   versions.

## 3. Architecture cible

```text
ARC Agent
├── mémoire immédiate de la conversation
├── mémoire permanente courte
│   ├── USER.md
│   └── MEMORY.md
└── ARCenal Knowledge
    ├── corpus Markdown et pièces jointes
    ├── métadonnées documentaires
    ├── index plein texte
    ├── index sémantique
    ├── historique des versions
    ├── wiki salarié
    └── LDA calculée
```

L'intégration à ARC doit rester périphérique au moteur Hermes : connecteur,
plugin, service ou MCP spécialisé avant toute modification du cœur commun.

## 4. Modèle documentaire minimal

Chaque version documentaire porte au minimum les données suivantes :

```yaml
---
reference: PR-QSSE-001
titre: Gestion documentaire
type: Procedure
version: 4
statut: Applicable
date_application: 2026-09-22
proprietaire: Direction Q&D
approbateur: Direction générale
prochaine_revue: 2027-09-22
perimetre: ONYX
source: Interne
---
```

Les statuts de référence sont :

```text
Brouillon → En révision → À approuver → Applicable → Archivé
```

Pendant une révision, deux versions peuvent donc coexister :

```text
Version 4 → Applicable
Version 5 → En révision
```

Après approbation, la version 5 devient applicable, la version 4 est archivée
et la LDA est actualisée automatiquement.

## 5. Amélioration continue

Le wiki propose une action **Proposer une amélioration** sur chaque document.
La demande conserve l'auteur, la date, le motif, le document et la version
concernés. Elle suit ensuite ce parcours :

```text
Retour terrain
→ suggestion d'amélioration
→ ouverture d'une révision
→ modification du document
→ relecture et approbation
→ publication de la nouvelle version
→ mise à jour automatique de la LDA
→ archivage de l'ancienne version
```

ARC peut rechercher les éléments concernés, comparer la demande au contenu,
repérer les références obsolètes ou contradictoires et proposer une révision.
La publication d'une version applicable reste soumise au workflow
d'approbation.

## 6. Fonctions attendues d'ARC

ARC doit pouvoir :

- répondre à une question en citant la référence, la version et le passage ;
- retrouver la version applicable d'un document ;
- filtrer les documents par périmètre, type, propriétaire ou statut ;
- signaler les revues arrivant à échéance ;
- détecter les liens vers une version obsolète et les contradictions probables ;
- préparer une synthèse ou une revue documentaire ;
- créer une proposition de modification sans publier seul une version ;
- alimenter le wiki salarié avec les seules informations autorisées.

## 7. Interface du troisième volet

Le volet **RAG** du tableau de bord ARC comportera au minimum :

- une recherche conversationnelle avec sources ;
- l'accès au wiki documentaire ;
- une vue LDA filtrable et exportable ;
- les documents en révision ou en attente d'approbation ;
- les alertes de revue, d'obsolescence et d'incohérence ;
- les demandes issues de l'amélioration continue.

## 8. Base logicielle à sélectionner

Les candidats prioritaires sont **Wiki.js** et **BookStack**, à évaluer sur une
installation YunoHost représentative. SilverBullet reste une piste pour un
usage Markdown programmable, mais ne suffit pas seul à la maîtrise documentaire
QSSERP attendue.

La sélection finale devra vérifier :

- licence et pérennité du projet ;
- disponibilité ou maintenabilité d'un paquet YunoHost ;
- authentification SSO et gestion fine des droits ;
- API documentée et événements exploitables ;
- historique, révisions et restauration ;
- stockage exportable sans verrouillage propriétaire ;
- performances d'indexation et sauvegarde ;
- séparation entre contenu salarié et contenu d'administration.

## 9. Hors périmètre de cette décision

Ce document ne choisit pas encore le moteur vectoriel, le modèle d'embeddings,
le wiki final ni le protocole d'indexation. Ces choix techniques devront être
comparés sur l'instance YunoHost cible sans modifier les principes précédents.

