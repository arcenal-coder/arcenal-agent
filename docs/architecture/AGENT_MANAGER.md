# Agent Manager

## Rôle

`AgentManager` fournit quatre opérations génériques : lister, récupérer,
enregistrer et mettre à jour un agent. Il ne contient aucune branche propre à
ARC ou à ATS. Les spécialisations sont des données conformes au même contrat.

Le registre initial contient :

| Agent | Application | Rôle | Autonomie |
|---|---|---|---|
| `arc` | `arcenal-system` | `system-architect` | `approval_required` |
| `ats` | `arcenal-ats` | `recruitment` | `controlled` |

L'interface d'administration utilise les routes du plugin pour afficher le
registre et modifier uniquement `enabled`, `autonomy_level` et `model_policy`.
Chaque changement est écrit de façon atomique. Aucun bouton d'édition d'un
champ non persisté n'est présenté.

Les `knowledge_scopes` sont désormais exécutoires : ils alimentent le
`ContextPlan` et limitent les documents avant toute recherche. Ajouter un agent
sans définir son périmètre documentaire n'ouvre donc aucun accès implicite.

## Refus contrôlés

- un identifiant absent produit `AgentNotFoundError` sans repli vers ARC ;
- un agent désactivé produit `AgentDisabledError` avant toute inférence ;
- un registre illisible produit `AgentContractError` au lieu de revenir
  silencieusement aux valeurs par défaut ;
- un identifiant déjà enregistré est refusé.

## Extension

Un nouvel agent est ajouté en construisant une `AgentDefinition` puis en
l'enregistrant. Providers, moteur, sécurité, audit et Context Builder ne sont
pas dupliqués. Le guide complet se trouve dans
`docs/development/CREATE_AGENT.md`.
