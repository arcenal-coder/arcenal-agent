# Frontières de confiance

Trois identités sont distinctes :

1. YunoHost/SSOwat authentifie l'utilisateur et injecte `Remote-User` sur les routes protégées.
2. Une application prouve son identité par un jeton Bearer dédié et peut transmettre un utilisateur métier. Si SSOwat fournit aussi un utilisateur, les deux valeurs doivent correspondre.
3. Agent Manager sélectionne l'agent et calcule ses permissions côté serveur. Le client ne peut fournir ni permission, ni prompt système, ni politique de modèle.

Le rejet de l'application, du jeton, de l'utilisateur contradictoire, de l'agent inconnu, désactivé ou hors périmètre précède tout appel LLM. Les ACL documentaires, la confidentialité, `local_only`, le cache et les workflows utilisent le contexte effectif calculé par ARC.

Les headers d'identité ne sont fiables que derrière la configuration Nginx/SSOwat du paquet. Une exposition directe du port local du backend est interdite.
