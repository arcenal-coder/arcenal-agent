# État initial du RAG avant le lot 02

> Cette cartographie décrit la baseline du lot 0. L'architecture active du lot
> 02 est documentée dans [RAG.md](RAG.md).

## Ce qui existe

ARC dispose d’une première récupération documentaire, mais pas encore d’un RAG
sémantique vectoriel.

- Corpus canonique : Markdown sous `$HERMES_HOME/knowledge`.
- Métadonnées : frontmatter YAML simplifié, avec référence, type, version,
  statut, dates, propriétaire, approbateur et périmètre.
- Recherche : découpage lexical par mots, score pondéré sur référence, titre et
  occurrences dans le corps.
- Résultats : document, chemin, référence, version, statut et score.
- Lecture : second appel borné par chemin sûr pour obtenir le document choisi.
- Intégration agent : outils `arcenal_knowledge_search` et
  `arcenal_knowledge_document`.
- Traçabilité : le modèle peut citer la source recherchée ; la source reste le
  fichier Markdown, pas un fragment opaque.
- Permissions : administration protégée par le déploiement YunoHost ; le wiki
  ne retourne que les documents `Applicable`.

## Paramètres techniques observés

| Élément | État actuel |
|---|---|
| Moteur vectoriel | absent |
| Modèle d’embedding | absent |
| Chunks | document entier pour le score lexical |
| Taille / overlap | non applicable |
| Index persistant | aucun index ARC distinct ; parcours des Markdown |
| Reranking | score lexical déterministe uniquement |
| Filtres | statut via vues LDA/wiki ; métadonnées disponibles |
| Contexte final | résultat recherché puis document lu par outil |
| Pièces jointes | stockées et liées, non extraites/indexées |

Le FTS5 de `state.db` indexe les conversations Hermes ; il ne constitue pas
l’index du coffre documentaire ARC.

## Ce qui est réutilisable

- format Markdown portable et métadonnées ;
- chemins sûrs, écritures atomiques et limites de taille ;
- workflow documentaire et version applicable ;
- API de recherche/lecture et outils agent ;
- citations basées sur une identité documentaire stable ;
- séparation entre wiki public autorisé et coffre administrateur.

## Ce qui doit être modifié

- découper le contenu en passages stables et versionnés ;
- introduire un index lexical dédié ou réutiliser FTS5 de manière isolée ;
- ajouter un index vectoriel reconstruisible ;
- filtrer par droits, périmètre, statut et agent avant la recherche ;
- fusionner puis reranker les résultats lexicaux et sémantiques ;
- produire un `ContextPlan` avec budget et citations structurées ;
- extraire les formats bureautiques autorisés dans un traitement asynchrone.

## Ce qui manque

- embeddings et choix du modèle ;
- politique de chunking et d’overlap ;
- file d’indexation, reprise et diagnostic ;
- suppression/réindexation transactionnelle par version ;
- évaluation de pertinence et jeux de questions ;
- gestion multi-collections et ACL au niveau du passage ;
- détection de contradictions et fraîcheur documentaire.

Le Lot 0 ne change pas cette recherche. La future indexation devra pouvoir être
entièrement reconstruite depuis le corpus sans perte de données.
