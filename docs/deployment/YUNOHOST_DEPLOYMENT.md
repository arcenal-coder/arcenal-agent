# Déploiement YunoHost

Le paquet responsable est le dépôt séparé `arcenal_ynh`. Le code applicatif reste dans `arcenal-agent` et le paquet référence une archive immuable avec son empreinte SHA-256.

L'installation crée l'utilisateur système, le répertoire applicatif remplaçable et `/var/www/arcenal/data` persistant. Elle construit les interfaces avant le démarrage, configure Nginx, SSOwat, systemd et les services de contrôle. Les registres ARC sont initialisés automatiquement au premier chargement du runtime.

La permission principale est réservée aux administrateurs et demande l'injection d'identité SSOwat. Nginx transmet `Remote-User` au backend. L'API inter-applications conserve séparément le jeton applicatif et l'utilisateur ; une identité transmise par l'application qui contredit SSOwat est refusée.

La validation locale du paquet ne remplace pas une installation YunoHost. Installation fraîche, upgrade, redémarrage, sauvegarde, restauration et SSO doivent être marqués « TESTÉ » seulement après exécution sur une instance réelle.
