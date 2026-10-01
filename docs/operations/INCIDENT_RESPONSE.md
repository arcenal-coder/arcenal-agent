# Réponse aux incidents — ARCenal Agent

## Règles communes

1. Identifier l’heure, l’utilisateur, l’application et le `request_id`.
2. Préserver les journaux sans y ajouter de secret.
3. Vérifier si les données canoniques sont intactes avant toute réparation.
4. Préférer une action réversible et documentée.
5. Sauvegarder avant une migration, une restauration ou une correction de base.
6. Ne jamais utiliser le terminal agentique pour contourner le broker de
   contrôle.

## Provider indisponible

**Symptômes :** réponse IA impossible, code fournisseur `429`, `503` ou délai
dépassé.
**Vérifications :** état du fournisseur, modèle activé, quota, latence, politique
`local_only`, puis journaux expurgés.
**Action :** activer uniquement un fallback autorisé ou conserver le mode
dégradé. Ne jamais contourner `local_only`.
**Rétablissement :** un appel de test réussit et le fournisseur redevient sain,
sans rendre ARC dépendant de ce résultat pour son healthcheck global.

## Base SQLite verrouillée

**Symptômes :** `database is locked`, écritures différées ou erreurs répétées.
**Vérifications :** processus ARC actifs, durée des transactions, fichiers
`-wal` et `-shm`, espace disque et droits.
**Action :** arrêter proprement les écritures concurrentes puis redémarrer le
service. Ne jamais supprimer manuellement `-wal` ou `-shm` d’une base active.
**Rétablissement :** contrôle d’intégrité réussi, compte des données inchangé et
écriture témoin possible.

## RAG indisponible

**Symptômes :** recherche vide, index déclaré obsolète ou citations absentes.
**Vérifications :** présence des documents canoniques, ACL, état SilverBullet,
espace disque et métriques d’indexation.
**Action :** reconstruire l’index dérivé depuis l’interface. Ne jamais modifier
le statut documentaire pour forcer un résultat.
**Rétablissement :** la V2 applicable est trouvée, la V1 obsolète est exclue et
les citations pointent vers la bonne source.

## Échec SSO

**Symptômes :** redirection en boucle, identité absente, accès administrateur
refusé ou utilisateur non autorisé accepté.
**Vérifications :** permission YunoHost `arcenal.main`, SSOwat, Nginx et header
`YNH_USER` injecté.
**Action :** régénérer uniquement les configurations officielles concernées et
redémarrer Nginx après validation. Ne pas rendre la permission publique.
**Rétablissement :** administrateur accepté, utilisateur non connecté redirigé,
utilisateur hors groupe refusé, headers forgés ignorés.

## Disque plein ou erreur d’écriture

**Symptômes :** écriture impossible, base verrouillée, sauvegarde incomplète.
**Vérifications :** `df -h`, `df -i`, taille des journaux, archives et données.
**Action :** libérer uniquement des caches ou fichiers explicitement
reconstructibles. Ne supprimer aucune base, mémoire, LDA ou sauvegarde sans
validation humaine.
**Rétablissement :** espace de sécurité retrouvé, écriture atomique réussie et
service stable.

## Upgrade échoué

**Symptômes :** erreur YunoHost, service arrêté ou restauration automatique
incomplète.
**Vérifications :** journal complet de l’opération, archive pré-upgrade, état des
données et version des sources.
**Action :** laisser YunoHost restaurer l’archive pré-upgrade. Si nécessaire,
utiliser la procédure de restauration avec l’archive identifiée.
**Rétablissement :** ancienne version démarrée, données témoins intactes, SSO et
permissions conformes.

## Restore échoué

**Symptômes :** application absente, service non enregistré, source non
téléchargeable ou données manquantes.
**Vérifications :** intégrité de l’archive, disponibilité du tag épinglé,
répertoire de données, registre de services et droits.
**Action :** conserver l’archive et les données existantes ; corriger la cause
sur une cible de recette avant une nouvelle tentative.
**Rétablissement :** les trois services sont actifs, le jeu témoin correspond au
snapshot et les index dérivés sont reconstruits.

## Critères d’escalade immédiate

- secret visible dans un journal ou une réponse ;
- contournement du SSO, des ACL ou de `local_only` ;
- perte ou corruption de données canoniques ;
- restauration impossible ;
- service incapable de redémarrer après reboot.

Ces cas sont classés **BLOCKER** et interdisent toute Release Candidate.
