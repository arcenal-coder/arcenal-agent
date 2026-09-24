# Architecture du RAG, de la LDA et du wiki documentaire

Statut : **socle fonctionnel réalisé, index sémantique à compléter**
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

Le volet **RAG & LDA** d'ARC comporte :

- une recherche plein texte utilisable par ARC avec sources ;
- l'accès au wiki documentaire ;
- une vue LDA filtrable et exportable ;
- les documents en révision ou en attente d'approbation ;
- les alertes de revue arrivées à échéance ;
- les liens, liens entrants, tags et versions antérieures.

L'index sémantique par embeddings, la détection automatique de contradictions
et le traitement complet des demandes d'amélioration restent des évolutions du
socle. Leur absence ne change pas la portabilité du corpus ni les règles de
publication de la LDA.

## 8. Base logicielle retenue

Le socle est intégré à ARCenal Agent et repose sur des composants libres déjà
présents dans le projet : fichiers Markdown, API FastAPI et interface React.
Il reprend le modèle utile d'Obsidian — notes portables, liens `[[Wiki]]`, liens
entrants, tags et historique — sans dépendre d'un format propriétaire ni d'un
second service à administrer.

Ce choix apporte :

- une installation unique par le paquet YunoHost ;
- des documents sauvegardables et exportables sans verrouillage ;
- une séparation stricte entre l'administration et le wiki salarié ;
- une API bornée que le chat ARC peut interroger avec traçabilité ;
- la possibilité d'ajouter ultérieurement un moteur vectoriel sans migrer le
  corpus Markdown.

## 9. Hors périmètre de cette décision

Le moteur vectoriel et le modèle d'embeddings ne sont pas encore retenus. La
recherche lexicale actuelle reste la solution de repli déterministe ; leur ajout
ne devra modifier ni le format du corpus, ni les règles de publication.
