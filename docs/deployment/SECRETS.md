# Secrets en environnement YunoHost

Les secrets sont stockés dans `/var/www/arcenal/data/.env`, propriétaire `arcenal`, mode `0600`. Le registre des providers ne conserve que des références telles que `OPENROUTER_API_KEY`. L'interface indique qu'une clé est configurée sans jamais la renvoyer.

`ArcFileVault` est l’unique lecteur de ce fichier dans le périmètre ARC. Une
variable injectée dans le service systemd a priorité sans être recopiée sur le
disque. Le répertoire applicatif privé doit rester en `0700` et les écritures du
coffre sont atomiques.

Création, rotation et suppression passent par l’API native ARC Vault du panneau
ARC. Le navigateur ne reçoit que l’état configuré/non configuré. La rotation
remplace uniquement la variable ciblée et préserve les secrets des autres
fournisseurs. L'ancien jeton applicatif cesse immédiatement d'être accepté. La
suppression retire la ligne concernée ; la suppression complète de
l'application suit la politique de purge YunoHost.

Le répertoire de données est inclus dans les sauvegardes applicatives normales, donc les secrets suivent la protection et les droits de l'archive YunoHost. Une pré-sauvegarde `BACKUP_CORE_ONLY` d'upgrade peut les exclure : ils restent alors en place et ne doivent pas être recréés.

Aucun secret ne doit apparaître dans Git, les journaux, les fixtures, la documentation, les URL ou les arguments de processus.
