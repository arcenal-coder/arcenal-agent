# ARC Frugal

ARC Frugal répond d'abord à la question : « un LLM est-il nécessaire ? ». L'ordre d'exécution est déterministe, cache fiable, workflow validé, puis modèle routé. Chaque sortie porte le mode, la raison, le fournisseur et le modèle éventuels, les tokens, le coût et la durée.

Le classifieur est local et fondé sur des règles explicites. Le routage reste déterministe ; aucun LLM n'est appelé pour choisir un LLM. Un échec de workflow revient vers ARC Frugal et peut atteindre le routeur, sans contourner ARC Core, les ACL ni le Knowledge Engine.

Les économies sont nulles tant qu'aucune exécution LLM comparable n'a fourni de baseline. Elles sont ensuite calculées par couple agent/type de tâche à partir de la moyenne réellement observée.

## Ordre de confiance

ARC Frugal conserve l'ordre `Official Knowledge > Enterprise Memory > Conversation`. Les ACL sont appliquées avant le retrieval par le Context Builder, donc avant tout cache ou routage.
