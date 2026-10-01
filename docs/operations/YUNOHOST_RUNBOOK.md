# Manuel opérateur YunoHost — ARCenal Agent

Ce manuel s’applique au paquet `arcenal` installé par YunoHost. Les opérations
destructives s’exécutent uniquement après sauvegarde et sur une cible autorisée.
Les commandes nécessitant les droits d’administration sont lancées depuis la
console du serveur, jamais depuis le terminal agentique d’ARC.

## 1. Vérifier l’état

```bash
yunohost app info arcenal
yunohost service status arcenal
systemctl status arcenal arcenal_control arcenal_broker --no-pager
curl --fail --silent http://127.0.0.1:9119/ >/dev/null
```

Le service principal peut rester disponible en mode dégradé lorsqu’un provider
distant est en panne. La santé du fournisseur ne doit pas être confondue avec
la santé d’ARC, du wiki ou de la LDA.

## 2. Consulter les journaux

```bash
journalctl -u arcenal -u arcenal_control -u arcenal_broker --since "30 minutes ago" --no-pager
journalctl -u nginx --since "30 minutes ago" --no-pager
yunohost log list --limit 20
```

Avant tout partage, rechercher et expurger les clés, cookies, en-têtes
`Authorization`, mots de passe et contenus documentaires confidentiels.

## 3. Redémarrer

```bash
systemctl restart arcenal_broker arcenal_control arcenal
systemctl is-active arcenal_broker arcenal_control arcenal
```

Après redémarrage, contrôler l’accès SSO, une recherche LDA, une mémoire et le
provider configuré. Aucun fichier ne doit être corrigé manuellement pour
retrouver un état opérationnel.

## 4. Tester un provider

Utiliser **Paramètres > Fournisseurs IA > Tester**. Vérifier :

- le fournisseur et le modèle réellement retenus ;
- la latence, les tokens et le coût rapporté ;
- le `request_id` ;
- l’absence de secret dans les journaux.

Un échec doit produire un message contrôlé. Ne jamais copier la clé dans une
commande, un ticket ou un journal de recette.

## 5. Reconstruire les index

Utiliser l’action **RAG & LDA > Reconstruire l’index**, confirmer l’opération,
puis vérifier le nombre de documents et une citation témoin. L’index est dérivé
des documents canoniques ; sa reconstruction ne doit ni modifier leur statut ni
publier un brouillon.

Pour l’index historique des sessions Hermes, suivre
[`state-db-recovery.md`](../state-db-recovery.md).

## 6. Créer une sauvegarde

```bash
yunohost backup create --apps arcenal
yunohost backup list
```

Noter le nom, la taille, la durée et l’état final. La sauvegarde doit contenir
les données canoniques et l’état de contrôle. Les sources peuvent être
retéléchargées depuis l’archive épinglée. Les caches et index explicitement
dérivés peuvent être reconstruits.

## 7. Restaurer

La restauration réelle doit être testée sur une instance propre ou une cible de
recette réinitialisée :

```bash
yunohost backup restore NOM_ARCHIVE --apps arcenal --force
systemctl is-active arcenal_broker arcenal_control arcenal
```

Contrôler ensuite le jeu défini dans
[`YUNOHOST_TEST_DATASET.md`](../baseline/YUNOHOST_TEST_DATASET.md), les modes
des secrets, le SSO, le wiki, la LDA, les providers et la reconstruction des
index.

## 8. Mettre à niveau

```bash
yunohost app upgrade arcenal -u URL_DU_PAQUET_TESTE --debug
```

Une mise à niveau n’est acceptée qu’après comparaison du snapshot des données.
Ne pas remplacer l’upgrade par une désinstallation/réinstallation.

## 9. Rotation d’un secret

Effectuer la rotation depuis le panneau de configuration ou le coffre prévu.
La nouvelle valeur doit être écrite en `0600`, l’ancienne refusée et la nouvelle
validée par un test de connexion. Ne jamais afficher la valeur enregistrée.

## 10. Mode dégradé

En cas de panne provider, conserver en priorité :

- interface et SSO ;
- supervision YunoHost ;
- LDA, wiki et recherche locale ;
- mémoire ;
- exécution déterministe ;
- workflows locaux ;
- cache encore admissible.

Voir [`DEGRADED_MODE.md`](DEGRADED_MODE.md) pour les règles de routage.

## 11. Vérifier les permissions

```bash
stat -c '%a %U:%G %n' \
  /var/www/arcenal/data \
  /var/www/arcenal/data/config.yaml \
  /var/www/arcenal/data/.env \
  /var/lib/arcenal-control
```

Attendus : données et état de contrôle en `0700`, configuration et secrets en
`0600`. Répéter ce contrôle après upgrade et restauration.
