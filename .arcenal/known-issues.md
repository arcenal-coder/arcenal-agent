# Points ouverts

## CDC-GAP-001 — Conformité fonctionnelle incomplète

- État : audit terminé, architecture validée et réalisation engagée.
- Impact : la version ynh34 sécurise l'installation et fournit les trois volets,
  mais plusieurs domaines du CDC détaillé sont absents ou partiels, notamment
  six sections Paramètres, la gouvernance complète des agents, le système, la
  sécurité visible, les sauvegardes et le premier démarrage.
- Preuve : `docs/arcenal-product-audit.md` et
  `docs/arcenal-product-cdc-v2.md`.
- Prochaine étape : poursuivre les lots dans l'ordre défini par l'audit avec
  critères `AC-*` et recette installée.

## SEC-YH-001 — Recette YunoHost réelle requise

- État : ouvert.
- Impact : le découpage en trois services et les permissions des sockets ont
  été vérifiés statiquement et unitairement, mais pas encore installés sur la
  machine YunoHost de recette.
- Prochaine étape : construire un paquet de développement, tester la mise à
  jour depuis ynh32, puis vérifier les identités, groupes, sockets, SSOwat,
  sauvegarde, restauration et retour arrière.

## YNH-UPGRADE-001 — Relance de la mise à niveau ynh34 requise

- État : correctif publié, recette réelle en attente.
- Symptôme initial : la mise à niveau ynh33 s'arrêtait après la sauvegarde avec
  `Rien n'a été restauré` ; la sauvegarde cœur ne contenait aucun fichier et le
  démarrage du service de contrôle pouvait échouer avant la création du socket.
- Correctif : ynh34 crée le socket avec le groupe Nginx dès le démarrage et
  ajoute les unités systemd ainsi que la configuration Nginx à la sauvegarde
  cœur restaurable.
- Prochaine étape : actualiser le catalogue stable sur le serveur en ligne,
  relancer la mise à niveau et collecter le journal complet si elle échoue.

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
- Impact : la structure d'onglets est livrée pour les cinq panneaux déjà
  fonctionnels. Contexte, Directives, Mémoire, Outils, Système et Sauvegardes
  restent à développer sans écran factice ; le centre de sécurité doit encore
  être approfondi.
