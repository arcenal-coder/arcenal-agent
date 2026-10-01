# Intégration mémoire et RAG

## Chaîne de traitement

```text
Enterprise Memory Store
        ↓ normalisation
KnowledgeDocument(source_type=enterprise_memory)
        ↓ ACL
index lexical reconstruisible
        ↓ retrieval et budget
Enterprise Memory dans le Context Builder
```

Seules les mémoires actives sont projetées. Les ACL sont évaluées avant le classement des fragments. Les scopes, la confidentialité, l’application, l’agent, l’utilisateur et les permissions sont cumulatifs.

## Résultats typés

Les citations exposent `source_type`, `authority` et la provenance. `authority=enterprise_memory` empêche de présenter une mémoire comme une pièce officielle.

Le classement place les sources officielles avant la mémoire lorsqu’elles répondent à la même requête. La pertinence lexicale continue de départager les sources d’un même niveau.

## Reconstruction

La reconstruction relit simultanément le coffre documentaire et SQLite. Elle exclut les entrées expirées, archivées ou supprimées et remplace atomiquement l’index dérivé.
