# Cache sémantique ARC Frugal

La clé exacte couvre l'agent, la requête normalisée, le contexte applicatif, les versions des sources et la signature des permissions. Une réponse issue d'ARC administrateur ne peut donc pas servir un agent ATS.

Le rapprochement sémantique utilise une similarité lexicale locale et un seuil explicite fourni au cache. Seules les réponses validées sont réutilisables sémantiquement. Une réponse générée reste limitée à la clé exacte et expire plus vite.

Chaque entrée conserve les dépendances documentaires, l'agent, l'ACL, le modèle et les métriques disponibles. L'API d'invalidation cible un type et un identifiant. Les événements à relayer sont : nouvelle LDA ou version documentaire, wiki modifié, mémoire corrigée/expirée/supprimée, ACL ou agent modifié, règle ou workflow modifié, fournisseur modifié et modèle désactivé.

Le cache n'est jamais une source de vérité : en cas de doute ou de dépendance différente, la réponse est un cache miss.
