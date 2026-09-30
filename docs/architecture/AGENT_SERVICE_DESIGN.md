# Conception du futur service d’agents

Statut : conception préparatoire, aucune API publique créée dans le Lot 0.

## Position dans l’existant

Le point d’entrée recommandé est un routeur FastAPI du plugin
`arcenal-supervisor`, monté par `hermes_cli/web_server.py`. Il doit appeler un
service Python indépendant du transport qui résout un profil puis utilise la
boucle agentique existante.

```text
Application ARCenal
  → authentification de service
  → délégation utilisateur vérifiée
  → AgentService
  → profil spécialisé + politique + ContextPlan
  → AIAgent Hermes
  → réponse + citations + usage + audit
```

## Requête logique

Une requête future doit contenir :

- identifiant et version de l’application appelante ;
- identifiant de requête et clé d’idempotence ;
- identité technique authentifiée ;
- identité utilisateur déléguée, rôle et groupes prouvés ;
- identifiant stable de l’agent demandé ;
- message et contexte applicatif borné ;
- portées demandées ;
- niveau d’autonomie autorisé ;
- budget temps/tokens et collections RAG permises.

## Réponse logique

- identifiant de requête ;
- état `completed`, `pending_approval`, `failed` ou `cancelled` ;
- réponse destinée à l’utilisateur ;
- citations structurées ;
- actions proposées ou exécutées ;
- provider/modèle logique sans secret ;
- usage disponible ;
- référence d’audit et erreur métier stable.

## Authentification et autorisation

- Même serveur : socket Unix avec permissions de groupe dédiées, ou mTLS sur
  boucle locale.
- Plusieurs hôtes : mTLS avec certificats courts et appairage explicite.
- L’identité de service n’accorde aucune permission métier par elle-même.
- La délégation utilisateur est vérifiée auprès de l’autorité YunoHost ou du
  fournisseur d’identité retenu ; un simple en-tête provenant d’Internet est
  insuffisant.
- Chaque agent possède une liste de portées, outils, collections et actions.
- Les mutations sensibles réutilisent préparation et confirmation ARC.

## Route future

`POST /api/v1/agents/{agent}/query` est acceptable après mise en place du
middleware d’identité inter-applications. La version doit porter sur le contrat
HTTP ; les profils et prompts disposent de leur propre version interne.

Erreurs minimales : `invalid_request`, `unauthenticated`, `forbidden`,
`agent_not_found`, `approval_required`, `provider_unavailable`,
`budget_exceeded`, `timeout` et `internal_error`. La réponse ne révèle ni clé,
ni chemin privé, ni trace Python.

## Audit

Chaque étape partage un identifiant de corrélation. Les logs enregistrent
application, utilisateur pseudonymisé si nécessaire, agent, modèle, outils,
état, durée et usage. Le texte complet et les secrets sont exclus par défaut.

## Compatibilité AACP/1

Le service d’agents répond aux applications ; AACP/1 permet à ARC d’appeler les
capacités de ces applications. Les deux sens sont complémentaires et doivent
partager identité, portées, idempotence et corrélation sans exposer le provider
LLM directement.
