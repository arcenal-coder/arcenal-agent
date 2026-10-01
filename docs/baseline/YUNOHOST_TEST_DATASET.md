# Jeu de données témoin YunoHost — Lot 07

Statut : définition figée, injection réelle à effectuer sur l’instance dédiée.

Ce jeu permet de comparer installation, upgrade, redémarrage, sauvegarde et
restauration. Toutes les valeurs sont fictives et ne contiennent aucune donnée
personnelle ou confidentielle.

## Identifiants attendus

| Domaine | Identifiant témoin | État attendu |
|---|---|---|
| Agent personnalisé | `lot07-agent-maintenance` | actif |
| Provider | `lot07-openrouter` | actif, secret stocké séparément |
| Modèle | `lot07-model-primary` | associé au provider témoin |
| Mémoire factuelle | `lot07-memory-fact-001` | active |
| Décision | `lot07-memory-decision-001` | active |
| Projet | `lot07-memory-project-001` | actif |
| Document wiki | `LOT07-WIKI-001` | applicable et visible |
| Document LDA V1 | `LOT07-LDA-001-v1` | archivé ou obsolète |
| Document LDA V2 | `LOT07-LDA-001-v2` | applicable |
| Workflow | `lot07-workflow-report` | actif |
| Cache ou métrique | `lot07-cache-deterministic` | identifiable |

## Contenu non sensible

- Le document wiki contient une procédure fictive de contrôle quotidien.
- La V1 LDA indique « version obsolète » et ne doit jamais être citée comme
  applicable.
- La V2 LDA indique « version applicable » et doit être la seule version
  retenue par ARC.
- Les mémoires utilisent des formulations génériques sans nom de personne,
  client, fournisseur réel ou infrastructure réelle.
- Le workflow produit un rapport local sans envoi externe.

## Snapshot avant opération

Avant upgrade et avant backup, consigner dans le journal sécurisé :

```text
agent_count
provider_count
model_count
memory_count
document_count
lda_applicable_count
workflow_count
cache_entry_count
```

Pour chaque témoin, conserver :

- son identifiant stable ;
- sa version ;
- son statut ;
- son empreinte SHA-256 lorsque le format est stable ;
- la date du snapshot ;
- le `request_id` de l’opération de création lorsqu’il existe.

Les secrets sont contrôlés seulement par présence, permission et capacité de
connexion. Leur valeur ne doit jamais entrer dans le snapshot.

## Contrôle après opération

Le contrôle est réussi uniquement si :

- tous les identifiants attendus sont présents ;
- les nombres ne diminuent pas sans raison documentée ;
- les empreintes des données canoniques restent identiques ;
- V1 reste non applicable et V2 reste applicable ;
- le secret fonctionne encore ou suit la stratégie de réinjection documentée ;
- les index dérivés exclus de la sauvegarde sont reconstruits avec succès.
