# Gouvernance de la mémoire

## Autorité

Une mémoire n’est jamais une règle officielle. L’ordre de décision est : politique système, LDA applicable, document officiel applicable, règle métier validée, mémoire d’entreprise, conversation.

Une contradiction reste traçable, mais le document officiel applicable demeure prioritaire.

## Cycle de vie

- `active` : utilisable par le RAG selon les ACL ;
- `pending_review` : visible en administration, non injectée ;
- `archived` : conservée, non injectée ;
- `expired` : arrivée à échéance, non injectée ;
- `deleted` : suppression logique, non injectée.

La suppression physique efface l’entrée et son historique du stockage canonique. La reconstruction qui suit retire aussi ses fragments de l’index dérivé.

## Matrice

| Type | Conservation | Source requise | ACL | Expiration possible |
|---|---|---|---|---|
| Fait | Variable | Oui | Oui | Oui |
| Décision | Longue ou permanente | Oui | Oui | Oui |
| Personne | Variable | Oui | Oui | Oui |
| Projet | Longue | Oui | Oui | Oui |
| Règle | Longue | Oui | Oui | Oui |
| Préférence | Variable | Oui | Oui | Oui |

## Provenance et audit

La provenance identifie le canal, la source, la date, l’auteur et, lorsqu’ils existent, la requête, l’agent et l’application. Les événements d’audit enregistrent l’acteur, l’action et l’identifiant de mémoire, jamais le contenu complet.

Une correction crée une révision avec l’ancienne et la nouvelle valeur, son auteur, sa date et son motif. Les créations issues d’un agent ou d’une conversation passent en `pending_review`.
