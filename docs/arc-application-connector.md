# Manuel d’intégration des applications avec ARC

**Contrat :** ARC Application Connector Protocol 1.0 (`AACP/1`)

**Statut :** spécification de préparation — aucun connecteur métier n’est livré
**Cible :** applications ARCenal empaquetées pour YunoHost 12 stable

Ce manuel définit comment une application ARCenal doit exposer ses fonctions à
ARC, l’agent administrateur d’ARCenal Système. Il permet de préparer dès
aujourd’hui une application comme l’ATS, la veille réglementaire ou une
application documentaire, sans créer immédiatement son connecteur.

Le protocole sépare trois responsabilités :

- ARC administre YunoHost et orchestre les agents ;
- l’agent spécialisé applique une mission, des skills et une politique de
  modèle ;
- l’application reste seule propriétaire de ses données et de ses règles
  métier.

Une application ne fournit jamais de terminal, de requête SQL libre ou de
point d’entrée permettant d’exécuter une commande arbitraire. Elle publie des
capacités métier nommées et validées.

## 1. Principes obligatoires

Une intégration conforme respecte les règles suivantes :

1. **Refus par défaut.** Une capacité absente du manifeste est interdite.
2. **Moindre privilège.** Chaque agent reçoit uniquement les permissions utiles
   à sa mission.
3. **Identité par instance.** Deux installations d’une même application ont des
   certificats et des identifiants distincts.
4. **Plan avant mutation.** Toute écriture peut être examinée avant son
   exécution.
5. **Confirmation des destructions.** ARC ne contourne jamais la confirmation
   humaine exigée pour une action destructive.
6. **Idempotence.** Une répétition réseau ne doit pas créer deux opérations.
7. **Traçabilité.** Chaque appel porte un identifiant corrélable aux journaux
   d’ARC et de l’application.
8. **Aucun secret dans le manifeste.** Les secrets restent dans des fichiers
   protégés ou dans le magasin de secrets d’ARC.
9. **Transport local.** Une application installée sur le même serveur n’expose
   pas son connecteur directement à Internet.
10. **Données délimitées.** L’agent ne peut rechercher que dans les espaces et
    collections explicitement associés à son profil.

## 2. Architecture de référence

```text
Administrateur YunoHost
        │
        ▼
Interface ARC ── Chat / Agents / RAG
        │
        ▼
Service d’orchestration ARC
        │  AACP/1 + mTLS
        ├──────────────► Application ATS
        ├──────────────► Application Veille
        └──────────────► Application documentaire
```

Le connecteur écoute sur une adresse de boucle locale. Un socket Unix est
préféré lorsqu’il est pris en charge par l’application. Le service ARC vérifie
que l’adresse déclarée est locale et refuse les URL arbitraires afin de limiter
les attaques SSRF.

Transports autorisés :

- socket Unix avec permissions système dédiées ;
- HTTPS sur `127.0.0.1` ou `::1` avec authentification mutuelle TLS ;
- HTTPS privé entre deux hôtes ARCenal explicitement appairés.

Le protocole applicatif utilise JSON sur HTTPS. Les traitements longs sont
asynchrones et renvoient un identifiant de tâche. Les événements utilisent des
webhooks signés ou un flux Server-Sent Events local.

## 3. Enregistrement dans YunoHost

Le paquet YunoHost de l’application installe un manifeste dans :

```text
/etc/arcenal/connectors.d/<app_instance>.json
```

Le fichier appartient à `root:arcenal-connectors`, est en mode `0640` et ne
contient aucun secret. ARC surveille ce répertoire et recharge les manifestes
au démarrage ou après une notification explicite du paquet.

Un paquet ne modifie jamais directement la configuration interne d’ARC. Lors
de sa suppression, il retire son manifeste et révoque son certificat.

### 3.1 Exemple de manifeste

```json
{
  "protocol": "AACP/1",
  "application": {
    "id": "arcenal-ats",
    "instance": "arcenal-ats__2",
    "name": "ARCenal ATS",
    "version": "1.4.0~ynh3"
  },
  "transport": {
    "type": "https",
    "base_url": "https://127.0.0.1:9443/arc/v1",
    "server_name": "arcenal-ats__2.local"
  },
  "identity": {
    "certificate": "/etc/arcenal/identities/arcenal-ats__2/client.crt",
    "private_key_ref": "arcenal://identities/arcenal-ats__2/client-key"
  },
  "capabilities_endpoint": "/capabilities",
  "health_endpoint": "/health",
  "events": {
    "mode": "webhook",
    "catalog_endpoint": "/events/catalog"
  },
  "rag": {
    "collections_endpoint": "/rag/collections",
    "search_endpoint": "/rag/search"
  }
}
```

`private_key_ref` est une référence opaque. Une clé privée ou un jeton ne doit
jamais apparaître dans ce fichier.

## 4. Identité et authentification

### 4.1 Communications de service

ARC et l’application utilisent une authentification mutuelle TLS :

- ARC possède une autorité de certification locale dédiée aux connecteurs ;
- chaque instance reçoit un certificat client et un certificat serveur ;
- les certificats sont courts, renouvelables et révoqués à la désinstallation ;
- l’identité vérifiée correspond exactement à l’instance du manifeste ;
- TLS 1.2 au minimum est requis, TLS 1.3 est recommandé.

Le certificat authentifie le service, mais n’accorde aucune permission à lui
seul. Les permissions viennent du profil d’agent et des portées déclarées.

### 4.2 Délégation d’un utilisateur

Lorsqu’une action doit respecter les droits d’un utilisateur métier,
l’application utilise OAuth 2.1 avec :

- code d’autorisation et PKCE ;
- URI de redirection enregistrée exactement ;
- jeton d’accès de courte durée ;
- rotation des jetons de renouvellement ;
- portées limitées à l’application et à l’agent ;
- révocation immédiate depuis ARC ou depuis l’application.

Le flux `client_credentials` n’est pas utilisé pour imiter un utilisateur. Les
actions de service restent attribuées à l’identité technique de l’agent.

## 5. Modèle de permissions

Une portée suit la forme :

```text
<ressource>:<action>[:<périmètre>]
```

Exemples :

```text
candidates:read
candidates:update:assigned
documents:read:recruitment
alerts:create
reports:generate
```

Les portées génériques telles que `admin`, `all` ou `*` sont interdites dans
un connecteur métier. Les droits d’administration de YunoHost appartiennent à
ARC et ne sont pas transmis aux agents spécialisés.

Chaque capacité précise son niveau de risque :

- `read` : aucune modification ;
- `write` : modification réversible ou bornée ;
- `sensitive` : donnée confidentielle ou effet étendu ;
- `destructive` : suppression, écrasement ou révocation difficile à annuler.

ARC peut exécuter automatiquement les niveaux `read`, `write` et `sensitive`
si sa politique l’autorise. Le niveau `destructive` exige toujours une
confirmation explicite d’un administrateur YunoHost.

## 6. Catalogue des capacités

L’application expose :

```http
GET /arc/v1/capabilities
```

Exemple de réponse :

```json
{
  "protocol": "AACP/1",
  "capabilities": [
    {
      "id": "candidate.list",
      "version": "1.0",
      "summary": "Lister les candidatures accessibles à l’agent",
      "risk": "read",
      "required_scopes": ["candidates:read"],
      "supports_plan": false,
      "supports_idempotency": true,
      "input_schema": {
        "type": "object",
        "properties": {
          "status": {"type": "string"},
          "limit": {"type": "integer", "minimum": 1, "maximum": 100}
        },
        "additionalProperties": false
      }
    }
  ]
}
```

Les schémas suivent JSON Schema 2020-12. Toute donnée entrante est validée
avant d’atteindre la logique métier. Une propriété inconnue est refusée par
défaut.

## 7. Exécution d’une action

### 7.1 Préparation

Une capacité mutable expose un plan :

```http
POST /arc/v1/actions/<capability_id>/plan
```

En-têtes obligatoires :

```text
X-ARC-Request-ID: UUID
X-ARC-Agent-ID: identifiant stable
Idempotency-Key: UUID
Content-Type: application/json
```

La réponse décrit les effets sans les appliquer :

```json
{
  "plan_id": "plan_01J...",
  "expires_at": "2026-09-22T15:10:00Z",
  "risk": "write",
  "summary": "Affecter la candidature C-1042 au poste P-18",
  "effects": [
    {
      "resource": "candidate:C-1042",
      "operation": "update",
      "fields": ["position_id"]
    }
  ],
  "reversible": true
}
```

### 7.2 Exécution

```http
POST /arc/v1/actions/<capability_id>/execute
```

Le corps référence le plan encore valide :

```json
{
  "plan_id": "plan_01J...",
  "input": {
    "candidate_id": "C-1042",
    "position_id": "P-18"
  }
}
```

Une action rapide renvoie `200`. Une action longue renvoie `202` avec une
tâche consultable :

```json
{
  "job_id": "job_01J...",
  "status": "queued",
  "status_url": "/arc/v1/jobs/job_01J..."
}
```

L’application conserve le résultat associé à `Idempotency-Key`. Une répétition
identique retourne le même résultat. Une répétition avec un corps différent
renvoie `409 idempotency_conflict`.

## 8. Ressources et RAG

Le connecteur peut exposer des collections documentaires sans donner à ARC un
accès direct à la base de données ou au système de fichiers de l’application.

Routes recommandées :

```http
GET  /arc/v1/rag/collections
POST /arc/v1/rag/search
GET  /arc/v1/rag/documents/<document_id>
```

Chaque résultat contient au minimum :

- un identifiant stable ;
- le titre et le type du document ;
- la collection ;
- la date de mise à jour ;
- les droits ayant autorisé le résultat ;
- une référence de citation ;
- le contenu ou un extrait borné.

Une application peut choisir entre deux modes :

- **recherche distante** : l’application indexe et filtre elle-même ;
- **indexation déléguée** : ARC reçoit des documents autorisés et maintient un
  index séparé par collection et par agent.

Le manifeste déclare le mode disponible. Une collection privée n’est jamais
fusionnée silencieusement avec la mémoire générale d’ARC.

## 9. Événements et notifications

Une application publie un catalogue d’événements versionnés, par exemple :

```text
candidate.created.v1
candidate.status_changed.v1
document.updated.v1
alert.raised.v1
```

Un événement contient :

```json
{
  "event_id": "evt_01J...",
  "event_type": "candidate.created.v1",
  "occurred_at": "2026-09-22T14:30:00Z",
  "application_instance": "arcenal-ats__2",
  "resource": {"type": "candidate", "id": "C-1042"},
  "data": {"position_id": "P-18"}
}
```

Les webhooks sont signés avec une clé distincte des certificats TLS. La
signature couvre le corps brut, l’horodatage et l’identifiant d’événement.
ARC refuse un événement trop ancien, déjà traité ou signé avec une clé
révoquée.

Une notification par courriel est décidée par ARC après traitement de
l’événement. Une application ne reçoit jamais les identifiants de la boîte
mail d’ARC.

## 10. Santé et disponibilité

```http
GET /arc/v1/health
```

Cette route ne divulgue aucune donnée métier et renvoie :

```json
{
  "status": "ready",
  "protocol": "AACP/1",
  "application_version": "1.4.0~ynh3",
  "connector_version": "1.0.0",
  "dependencies": [
    {"name": "database", "status": "ready"}
  ]
}
```

Valeurs admises : `ready`, `degraded`, `unavailable`. Une dépendance sensible
n’expose ni adresse, ni nom d’utilisateur, ni message contenant un secret.

## 11. Erreurs normalisées

Les erreurs utilisent `application/problem+json` :

```json
{
  "type": "https://docs.arcenal.fr/problems/scope-denied",
  "title": "Permission insuffisante",
  "status": 403,
  "code": "scope_denied",
  "detail": "La portée candidates:update:assigned est requise.",
  "request_id": "018f..."
}
```

Codes minimaux :

| Code | HTTP | Signification |
|---|---:|---|
| `invalid_request` | 400 | Entrée non conforme au schéma |
| `authentication_failed` | 401 | Identité technique invalide |
| `scope_denied` | 403 | Portée absente |
| `resource_not_found` | 404 | Ressource inaccessible ou absente |
| `idempotency_conflict` | 409 | Clé réutilisée avec une autre demande |
| `plan_expired` | 409 | Plan expiré ou déjà consommé |
| `confirmation_required` | 428 | Validation humaine obligatoire |
| `rate_limited` | 429 | Limite temporaire atteinte |
| `connector_unavailable` | 503 | Service indisponible |

Un message d’erreur ne contient jamais de trace complète, requête SQL, jeton,
mot de passe ou chemin privé.

## 12. Compatibilité et versions

- `AACP/1` désigne la version majeure du contrat.
- Une évolution additive conserve la même version majeure.
- Une suppression ou un changement de sens exige une nouvelle version majeure.
- Une capacité possède sa propre version fonctionnelle.
- ARC ignore une propriété inconnue dans une réponse, mais une application
  refuse une propriété inconnue dans une commande.
- Une application annonce les versions du protocole qu’elle accepte.

Une capacité dépréciée reste disponible pendant au moins deux versions
mineures de l’application, sauf correction de sécurité documentée.

## 13. Journalisation et conservation

ARC et l’application journalisent les mêmes identifiants :

- `request_id` ;
- `agent_id` ;
- `application_instance` ;
- `capability_id` ;
- `plan_id` et `job_id` lorsqu’ils existent ;
- décision d’autorisation ;
- résultat et durée ;
- identité de l’administrateur ayant confirmé une destruction.

Les données métier sensibles sont masquées. Les journaux de sécurité sont
protégés contre la modification par l’utilisateur système de l’application.
La durée de conservation est configurable et documentée.

## 14. Parcours d’intégration d’une application

1. Définir les ressources métier accessibles à un agent.
2. Décrire des capacités étroites plutôt qu’une API générique.
3. Classer le risque de chaque capacité.
4. Écrire les schémas d’entrée et de sortie.
5. Ajouter le plan pour chaque mutation.
6. Garantir l’idempotence des exécutions.
7. Déclarer les portées minimales.
8. Implémenter la santé et les erreurs normalisées.
9. Ajouter les collections RAG nécessaires, si elles existent.
10. Ajouter les événements utiles, sans exposer de secret.
11. Faire installer le manifeste et l’identité par le paquet YunoHost.
12. Tester l’intégration avec une instance ARC de développement.

## 15. Matrice de tests minimale

Une application compatible fournit des tests isolés couvrant :

- appel nominal d’une capacité autorisée ;
- manifeste incomplet ou version incompatible ;
- certificat absent, expiré et révoqué ;
- portée absente ;
- propriété inconnue ou type invalide ;
- collection ou liste vide ;
- caractères Unicode et tailles maximales ;
- répétition avec la même clé d’idempotence ;
- conflit de clé d’idempotence ;
- plan expiré ;
- action destructive sans confirmation ;
- événement signé, expiré, modifié et rejoué ;
- perte temporaire du connecteur ;
- absence de fuite de secret dans les erreurs et journaux.

Les tests unitaires simulent le réseau, les certificats, le stockage et les
services extérieurs. Un test d’intégration séparé vérifie le chemin réel sur
une VM YunoHost de recette.

## 16. Checklist de conformité

Une application peut afficher « Compatible ARC » lorsque toutes les cases sont
validées :

- [ ] paquet YunoHost v2 installable et désinstallable proprement ;
- [ ] manifeste `AACP/1` valide et sans secret ;
- [ ] transport limité à une cible locale ou appairée ;
- [ ] authentification mutuelle TLS opérationnelle ;
- [ ] permissions à granularité métier et refus par défaut ;
- [ ] validation JSON Schema à la frontière ;
- [ ] plan disponible avant chaque mutation ;
- [ ] confirmation obligatoire des destructions ;
- [ ] idempotence vérifiée ;
- [ ] journaux corrélables et expurgés ;
- [ ] santé et erreurs normalisées ;
- [ ] collections RAG cloisonnées, si applicables ;
- [ ] événements authentifiés et protégés contre le rejeu, si applicables ;
- [ ] tests nominaux, limites et échecs réussis ;
- [ ] révocation de l’identité lors de la désinstallation.

## 17. Éléments volontairement différés

Cette version définit le contrat mais ne livre pas encore :

- le SDK serveur AACP ;
- l’autorité de certification locale d’ARC ;
- l’outil de validation automatique des manifestes ;
- un connecteur ATS, Nextcloud ou veille réglementaire ;
- le catalogue public des capacités ;
- la certification automatisée « Compatible ARC ».

Ces composants seront développés lorsque le premier connecteur métier sera
retenu. Leur implémentation devra respecter ce contrat ou faire évoluer sa
version de façon explicite.
