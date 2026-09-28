# Points ouverts

## SEC-YH-001 — Recette YunoHost réelle requise

- État : ouvert.
- Impact : le découpage en trois services et les permissions des sockets ont
  été vérifiés statiquement et unitairement, mais pas encore installés sur la
  machine YunoHost de recette.
- Prochaine étape : construire un paquet de développement, tester la mise à
  jour depuis ynh32, puis vérifier les identités, groupes, sockets, SSOwat,
  sauvegarde, restauration et retour arrière.

## TEST-001 — Suite Python historique indisponible localement

- État : ouvert.
- Preuve : aucun environnement existant ne contient `pytest`, FastAPI et les
  dépendances de développement ; aucune installation n'a été autorisée.
- Couverture disponible : les nouveaux domaines utilisent `unittest` et la
  bibliothèque standard, les tests web et les tests shell du paquet passent.
- Prochaine étape : exécuter le lanceur canonique dans l'environnement de CI ou
  dans le paquet de recette disposant de ses dépendances verrouillées.

## UI-SETTINGS-001 — Onglets métier restants

- État : ouvert.
- Impact : la structure d'onglets est livrée pour les quatre panneaux déjà
  fonctionnels. Général, Contexte, Directives, Mémoire, Outils, Système,
  Sauvegardes et le centre de sécurité restent à développer sans écran factice.
