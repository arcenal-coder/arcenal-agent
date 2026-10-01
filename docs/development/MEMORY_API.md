# API de mémoire d’entreprise

L’API administrateur est montée sous `/api/plugins/arcenal-supervisor/memory/v1`. Elle exige l’identité administrateur transmise par le SSO YunoHost.

| Méthode | Route | Usage |
|---|---|---|
| `GET` | `/memory/v1` | Rechercher et filtrer |
| `POST` | `/memory/v1` | Créer |
| `GET` | `/memory/v1/metrics` | Lire les métriques agrégées |
| `GET` | `/memory/v1/{id}` | Lire la fiche et l’historique |
| `PATCH` | `/memory/v1/{id}` | Corriger avec un motif |
| `POST` | `/memory/v1/{id}/status` | Archiver, restaurer ou expirer |
| `DELETE` | `/memory/v1/{id}` | Suppression logique ou physique confirmée |

La recherche accepte `query`, `memory_type`, `status`, `source_type`, `scope`, `confidentiality`, `project`, `person`, `created_from` et `created_to`.

Une création exige `memory_type`, `summary`, `content`, `source_type`, `source_id` et au moins un `knowledge_scope`. Une source `agent` ou `conversation` demandée comme active est enregistrée en attente de validation.

La suppression physique exige `confirmed=true`, `physical=true` et un motif. Elle est irréversible pour le stockage actif et ses index dérivés.
