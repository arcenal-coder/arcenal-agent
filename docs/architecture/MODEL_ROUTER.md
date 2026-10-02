# Model Router

Le registre sépare `provider`, `model_name` et `capabilities`. Les capacités configurables sont `deterministic`, `light`, `standard`, `advanced` et `specialized`. Aucun modèle commercial n'est figé dans le code.

Le routeur filtre successivement l'état, la capacité, la fenêtre de contexte, les outils, la sortie structurée, la vision, la localisation, les listes de fournisseurs et modèles, le plafond de coût et la classe de confidentialité. Les règles globales sont combinées aux règles de l'agent ; le client ne fournit aucune politique de routage. `local_only` interdit tout fallback distant.

Le classement favorise un modèle local lorsqu'il est demandé, puis applique la priorité du fournisseur, le coût déclaré et la priorité du modèle. La décision contient une raison technique et la liste des fallbacks éligibles. Elle ne contient aucune chaîne de pensée.

Le fournisseur ne définit aucun modèle par défaut. Le modèle est toujours choisi par la politique AUTO ou FIXED de l'agent. Un registre vide provoque une erreur de configuration explicite et n'autorise jamais un appel direct à l'ancien fournisseur Hermes. Les installations historiques doivent connecter un fournisseur, synchroniser ses modèles puis attribuer une politique à chaque agent.

Une attribution FIXED est validée avant persistance : le modèle doit être actif, appartenir au fournisseur annoncé, respecter la contrainte locale et accepter le niveau de confidentialité exigé par l'agent. Le même contrôle est réappliqué à l'exécution par le Model Router.
