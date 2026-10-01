# Model Router

Le registre sépare `provider`, `model_name` et `capabilities`. Les capacités configurables sont `deterministic`, `light`, `standard`, `advanced` et `specialized`. Aucun modèle commercial n'est figé dans le code.

Le routeur filtre successivement l'état, la capacité, la fenêtre de contexte, les outils, la sortie structurée, la vision, la localisation, les listes de fournisseurs et modèles, le plafond de coût et la classe de confidentialité. Les règles globales sont combinées aux règles de l'agent ; le client ne fournit aucune politique de routage. `local_only` interdit tout fallback distant.

Le classement favorise un modèle local lorsqu'il est demandé, puis applique la priorité du fournisseur, le coût déclaré et la priorité du modèle. La décision contient une raison technique et la liste des fallbacks éligibles. Elle ne contient aucune chaîne de pensée.

Le modèle Hermes actif est importé une seule fois comme entrée de compatibilité lorsque sa configuration fournit un couple fournisseur/modèle. Si une installation historique ne fournit pas encore ces métadonnées et que le registre est vide, ARC conserve temporairement l'appel Hermes existant et trace explicitement cette route de compatibilité. Cette tolérance est refusée dès qu'une contrainte `local_only`, fournisseur, modèle ou coût existe. Dès qu'une entrée est enregistrée, tout appel passe par les politiques du Model Router.
