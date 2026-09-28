# Synchronisation avec Hermes Agent

ARCenal Agent conserve Hermes Agent comme moteur technique amont. Les fonctions
métier ARC doivent être ajoutées par plugin, page dédiée ou paquet YunoHost avant
toute modification du cœur commun.

## Références Git

- `origin` : dépôt ARCenal, branche `arcenal` ;
- `upstream` : dépôt officiel Hermes Agent ;
- la version commune connue doit être consignée dans `.arcenal/project-state.md`.

Le dépôt `upstream` est une configuration locale de travail : il n'est pas créé
automatiquement par le code du produit.

## Procédure de mise à jour

1. travailler depuis un arbre propre en préservant les changements utilisateur ;
2. récupérer la branche principale Hermes sans exécuter de script distant ;
3. mesurer les changements ARC et les conflits depuis la base commune ;
4. fusionner dans une branche de maintenance dédiée ;
5. conserver en priorité les points d'extension Hermes récents ;
6. reporter les adaptations ARC isolées, sans réintroduire un ancien cœur ;
7. exécuter linter, vérification des types, tests Python, tests web et paquet YunoHost ;
8. tester une installation puis une mise à jour YunoHost avec conservation des données ;
9. mettre à jour la base commune documentée seulement après ces validations.

## Fichiers communs sensibles

Les conflits sont particulièrement surveillés dans `hermes_cli/main.py`,
`hermes_cli/banner.py`, `toolsets.py`, `pyproject.toml`, `uv.lock`,
`web/src/App.tsx`, `web/src/lib/api.ts` et les configurations de construction.

Une évolution ARC qui nécessite une modification durable dans cette liste doit
documenter pourquoi un plugin ou une API d'extension ne suffit pas.
