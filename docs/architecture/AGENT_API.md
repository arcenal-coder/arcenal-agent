# API interne des agents

## Route versionnée

`POST /api/v1/agents/{agent_id}/query`

Corps accepté :

```json
{
  "message": "Quels candidats correspondent au poste ?",
  "session_id": "ats-2026-42",
  "context": {"job_id": "42"}
}
```

Tout champ supplémentaire est refusé. Le client ne peut donc transmettre ni
permission, ni instruction système, ni configuration d'agent ou secret de
modèle.

## Authentification

L'appel porte :

- `Authorization: Bearer <secret applicatif>` ;
- `X-ARCenal-Application: arcenal-ats` ;
- facultativement `X-ARCenal-User: utilisateur`.

Le secret est lu dans
`ARCENAL_APP_<IDENTIFIANT_APPLICATION>_TOKEN`. Il doit contenir au moins 43
caractères et 16 caractères distincts. Il peut être généré avec
`openssl rand -base64 48`. Les comparaisons utilisent un temps constant et le
secret n'est ni renvoyé ni journalisé.

L'identité applicative et l'identité utilisateur restent distinctes. Dans ce
lot, l'utilisateur est une assertion transmise par l'application authentifiée ;
une identité utilisateur signée ou dérivée de SSOwat reste l'évolution cible.

## Réponse et erreurs

La réponse contient `request_id`, `agent_id`, `response`, `status`,
`approval_required`, `sources`, `actions` et les métriques d'usage sûres.

- `401` : preuve applicative absente ou invalide ;
- `403` : application authentifiée hors du périmètre de l'agent ;
- `404` : agent inconnu ;
- `409` : agent désactivé ;
- `422` : payload invalide ou champ interdit ;
- `503` : moteur IA indisponible.

Les routes d'administration du registre restent sous
`/api/plugins/arcenal-supervisor/agents/registry` et bénéficient de la
protection administrateur du dashboard.
