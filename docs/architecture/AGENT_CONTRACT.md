# Contrat interne d'un agent

Les modèles Pydantic du paquet `arc_core` sont stricts, immuables et refusent
les champs inconnus.

## AgentDefinition

| Champ | Fonction |
|---|---|
| `id` | identifiant stable indépendant du libellé |
| `name`, `description`, `role` | identité fonctionnelle |
| `application` | seule identité applicative autorisée à l'invoquer |
| `system_instructions` | blocs identifiés et bornés |
| `permissions` | capacités explicites, refus par défaut |
| `tools` | ensembles d'outils réellement disponibles |
| `knowledge_scopes` | périmètres obligatoires appliqués par les ACL du RAG |
| `model_policy` | mode, préférence locale, providers et modèles admis |
| `autonomy_level` | `automatic`, `controlled` ou `approval_required` |
| `enabled` | coupe l'invocation sans supprimer la définition |
| `metadata` | métadonnées non secrètes d'intégration |

## EffectiveContext

Le contexte effectif combine la politique globale, le contrat agent et la
requête. Il porte l'identité corrélée, les permissions filtrées, les outils,
les connaissances, la politique modèle, le `ContextPlan`, les chunks retenus,
les citations et les métriques de récupération.

## ContextPlan

Ce contrat immuable contient l'identité de requête, les scopes, permissions,
statuts, types de source, plafond de confidentialité, requête, filtres et budget.
Il est créé exclusivement côté serveur.

L'identité comprend `request_id`, `user_id`, `application_id`, `agent_id`,
`session_id`, les permissions effectives et l'horodatage UTC. L'absence
d'utilisateur reste explicitement `null`.

## Agent ATS

L'agent ATS est lié à `arcenal-ats`. Il possède uniquement `ats.read` et
`lda.read`, aucun outil ATS fictif, et les scopes `ats`, `company` et
`recruitment`. Il n'obtient ni scope système, ni permission administrative.
