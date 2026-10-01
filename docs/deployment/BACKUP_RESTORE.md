# Sauvegarde et restauration

La source de vérité persistante est `/var/www/arcenal/data` : configuration, secrets, agents, documents, LDA, wiki, mémoire, modèles, providers et workflows. Le service de contrôle possède également `/var/lib/arcenal-control`.

Le paquet sauvegarde ces deux emplacements et les configurations systemd/Nginx utiles à une restauration du cœur. Après restauration, il retélécharge la source épinglée, reconstruit les environnements et interfaces, réapplique les services puis démarre ARC.

Les index documentaires et caches sont dérivés. Ils peuvent être sauvegardés avec le répertoire de données pour accélérer le retour en service, mais leur perte ne doit pas supprimer les sources documentaires. Une recette réelle doit vérifier leur reconstruction et l'intégrité de chaque donnée témoin après restauration.
