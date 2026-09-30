# Context Builder

## Responsabilité

Le Context Builder traduit une requête authentifiée en contexte minimal. Le
client ne fournit ni `ContextPlan`, ni permissions, ni scopes, ni niveau de
confidentialité. Ces valeurs proviennent du contrat de l’agent et de la
politique globale.

## Séquence

1. vérifier l’application autorisée par `AgentDefinition` ;
2. retirer les permissions interdites globalement ;
3. créer l’identité corrélée et son `request_id` ;
4. construire un `ContextPlan` immuable ;
5. interroger le RAG central ;
6. appliquer le budget de chunks, caractères et tokens estimés ;
7. remettre à Hermes les fragments et identifiants de citation autorisés.

Par défaut, le plan ne demande que les documents `Applicable`. Une recherche
d’historique doit être explicite et l’agent doit posséder `lda.history`.

## Budget

Le budget initial est de 6 chunks, 12 000 caractères et environ 3 000 tokens.
La sélection parcourt le classement déterministe et ignore tout fragment qui
ferait dépasser une limite. Toute la LDA, toute la mémoire et tout l’historique
ne sont donc jamais injectés.

Le contexte documentaire est placé dans le message comme donnée contrôlée,
jamais comme nouvelle instruction système. Cette séparation conserve le prompt
système stable et respecte le cache de conversation Hermes.
