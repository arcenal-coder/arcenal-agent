# Audit de conformité ARCenal Agent

Date : 28 septembre 2026

Référence : [CDC détaillé 2.0](arcenal-product-cdc-v2.md)

Version auditée : branche `arcenal`, application `v0.21.0-arcenal20`, paquet
YunoHost `0.21.0~ynh35`.

## 1. Architecture actuelle

- Le cœur Hermes fournit la conversation, les profils, fournisseurs, modèles,
  compétences, outils, mémoire, sessions et API web générales.
- La façade React ARC ajoute les routes ARC, Agents, RAG & LDA, Wiki et
  Paramètres, ainsi qu'un thème ARCenal sans barre latérale Hermes.
- Le plugin `arcenal-supervisor` injecte l'identité ARC, neuf outils spécialisés,
  les services métier, la supervision et le contrat de maintenance contrôlée.
- Le paquet YunoHost installe le moteur, une API de contrôle séparée et un
  broker privilégié sous trois identités et sockets distincts.
- Nginx et SSOwat réservent l'administration au groupe `admins` et exposent le
  wiki en lecture aux utilisateurs autorisés.
- Les données persistantes résident dans `/var/www/arcenal/data` et l'état de
  sécurité dans `/var/lib/arcenal-control`.

## 2. Héritage Hermes conservé

- boucle agentique et appels aux modèles ;
- passerelle de chat JSON-RPC, sessions et historique ;
- profils isolés utilisés comme base des agents spécialisés ;
- fournisseurs, modèles, clés, compétences, outils et mémoire ;
- API de configuration et de gestion des secrets ;
- mécanisme de plugins et sections du prompt système.

Les écrans techniques Hermes restent hors de la navigation métier ; leurs API
et mécanismes réutilisables demeurent disponibles derrière les parcours ARC.

## 3. Développements spécifiques ARC

- identité, prompt et outils ARC ;
- chat web rebrandé et historique archivable ou supprimable ;
- façade principale à trois volets et thème ARCenal ;
- administration complète d'agents spécialisés et de leur mémoire isolée ;
- coffre Markdown, pièces jointes, recherche, liens, historique, LDA, wiki et CSV ;
- fournisseurs multiples, modèles principal et secondaire et tests réels ;
- coffre de comptes et API avec niveau d'autonomie ;
- supervision YunoHost étendue, sécurité, sauvegardes et premier démarrage ;
- politique d'autorisation, confirmations à usage unique et audit chaîné ;
- broker root à catalogue fermé et pont YunoHost en lecture.

## 4. Intégration YunoHost

Le paquet v2 installe depuis une archive GitHub épinglée, construit l'interface,
crée les utilisateurs et groupes techniques, configure Nginx, SSOwat et trois
services systemd, puis sauvegarde les données et configurations essentielles.
L'administrateur est un utilisateur YunoHost existant. Le premier démarrage
contrôle identité, permissions, serveur et fournisseur IA ; la messagerie locale,
les sauvegardes et le diagnostic sont pilotés depuis les écrans ARC.

## 5. Sécurité observée

Le refus par défaut, les quatre niveaux, les cibles bornées, la séparation des
identités, les jetons à usage unique et l'audit expurgé sont actifs. Le modèle
ne dispose d'aucun interpréteur privilégié : il prépare une action, puis l'API
de contrôle authentifiée et le broker fermé assurent confirmation, exécution,
vérification et preuve.

## 6. Matrice CDC

| Domaine | État | Preuve et écart principal |
|---|---|---|
| Fork maintenable | EXISTANT | Surcouche plugin/paquet isolée, base amont tracée et surveillance Hermes hebdomadaire avec ticket GitHub. |
| Installation native | EXISTANT | Paquet v2 installable, actualisable, sauvegardable et doté d’un premier démarrage diagnostiqué. |
| Administrateur YunoHost | EXISTANT | SSOwat et groupe `admins`, propriétaire sélectionné à l'installation. |
| Identité de notification | EXISTANT | Expéditeur `arcenal@domaine`, destinataire configurable et test borné via le service mail YunoHost. |
| Trois volets principaux | EXISTANT | ARC, Agents et RAG & LDA sont les seules entrées métier. |
| Chat ARC | EXISTANT | Chat natif, erreurs, sessions, diagnostic factuel, proposition d’action, confirmation authentifiée et résultat vérifié. |
| Agents spécialisés | EXISTANT | Création et administration intégrées d’un profil isolé avec identité, mission, modèles principal et secondaire, compétences, outils et mémoire dédiée. |
| Connecteurs AACP/1 | EXISTANT | Contrat et manuel publiés ; aucun connecteur actif conformément au périmètre validé de cette version. |
| Coffre Markdown | EXISTANT | Création, lecture, édition, recherche, liens, historique et pièces jointes présents. |
| Cycle documentaire | EXISTANT | Transitions bornées, motif, approbation nominative YunoHost, archivage de la version applicable précédente, historique et restauration confirmée. |
| LDA | EXISTANT | Registre, filtres, archive, pagination et CSV présents. |
| Wiki | EXISTANT | Route séparée en lecture limitée aux documents applicables. |
| RAG traçable | EXISTANT | Recherche et lecture exposent chemin, référence, version, statut et extrait ; les directives ARC imposent leur citation et les tests vérifient les sources retournées. |
| Paramètres Général | EXISTANT | Identité, langue, fuseau, destinataire, adresse d’ARC dérivée du domaine, versions détectées et test réel via la messagerie YunoHost. |
| Paramètres Apparence | EXISTANT | Clair, sombre, système, couleurs, prévisualisation, import PNG/JPEG borné du logo et du favicon, et reprise de la personnalisation YunoHost. |
| Paramètres Contexte | EXISTANT | Éditeur Markdown, aperçu, auteur, date, historique, restauration confirmée et récupération ciblée de `CONTEXT.md`. |
| Paramètres Mémoire | EXISTANT | `MEMORY.md` dispose d’un parcours ARC de consultation, recherche, ajout, modification, suppression confirmée, historique et restauration. |
| Paramètres Directives | EXISTANT | Inventaire borné, édition, aperçu, historique et restauration de `AGENTS.md`, `RULES.md`, `SECURITY.md` et `TOOLS.md`, injectés dans les nouvelles sessions. |
| Fournisseurs IA | EXISTANT | OpenRouter, OpenAI, Anthropic, Mistral, Gemini, Ollama et API compatibles disposent d'une adresse contrôlée, d'un modèle principal et secondaire, d'une activation, d'un test réel et d'un état persistant expurgé. |
| Accès métier | EXISTANT | Comptes et API associent périmètre, permissions et autonomie ; ARC ne voit que les accès actifs, tandis que le test réel, l'état, la date et la désactivation restent gouvernés depuis Paramètres. |
| Outils et capacités | EXISTANT | L’inventaire distingue ARCenal et Hermes, expose état, permission, risque, confirmation et dernière utilisation ; les capacités Hermes configurables sont activables, les outils ARC critiques restent protégés. |
| Vue Système | EXISTANT | Santé, versions, CPU, mémoire, stockage, charge, services, applications, mises à jour, domaines, certificats, sauvegardes, diagnostics et erreurs sont lus via le broker YunoHost fermé. |
| Moteur de permissions | EXISTANT | Quatre niveaux, rôles, cibles et refus par défaut testés. |
| Passerelle privilégiée | EXISTANT | Séparée, fermée et suffisante au périmètre : diagnostics, services, Nginx, sauvegardes et notification ; toute action inconnue est refusée. |
| Confirmation renforcée | EXISTANT | Préparation, confirmation humaine contextualisée et jeton à usage unique sont unifiés dans le processus de contrôle séparé. |
| Centre de sécurité | EXISTANT | La vue administrateur présente identité YunoHost, rôles, passerelles, catalogue fermé, confirmations actives et journal d’audit chaîné. |
| Sauvegardes | EXISTANT | Centre natif, inventaire YunoHost, création et restauration confirmée ; données, configuration, RAG/LDA, mémoires et audit sont couverts par les scripts du paquet. |
| Premier démarrage | EXISTANT | Assistant persistant avec identité administrateur, passerelles, intégration YunoHost, fournisseur IA, diagnostic initial et report non destructif. |
| Tests de conformité CDC | EXISTANT | Matrice `AC-*`, tests unitaires et d’intégration, recette YunoHost et contrôles de publication sont versionnés. |

## 7. Risques techniques

1. La synchronisation d’un grand nombre de compétences ou d’outils effectue
   plusieurs écritures ; une interruption réseau peut laisser une spécialisation
   partiellement appliquée, explicitement signalée à l’administrateur.
2. Une restauration coupe temporairement l'API de contrôle ; le navigateur peut
   afficher une déconnexion avant que systemd ne relance l'instance restaurée.
3. Toute extension future du catalogue privilégié doit conserver schéma fermé,
   validation de cible, confirmation, vérification et test du retour arrière.
4. La recette installée reste à rejouer à chaque promotion sur la cible de
   validation en ligne, car les tests locaux ne simulent pas tous les services.

## 8. Architecture cible

- Conserver Hermes comme moteur et ses profils comme isolation des agents.
- Ajouter une couche de services ARC dans `arcenal-supervisor`, sans logique
  métier privilégiée dans React ni modification spécifique du cœur Hermes.
- Transformer Paramètres en route conteneur à onze modules indépendants,
  chacun raccordé à une API typée et à un stockage explicite.
- Unifier toute maintenance sur l'API de contrôle et le broker ; supprimer à
  terme le chemin de mutation parallèle après migration et tests.
- Ajouter des agrégateurs YunoHost en lecture pour système, applications,
  domaines, certificats, mises à jour, diagnostics et sauvegardes.
- Étendre le catalogue privilégié par petites chaînes complètes, avec schéma,
  permission, risque, confirmation, exécution, vérification et audit.
- Introduire des services versionnés pour contexte, mémoire et directives,
  avec historique atomique et contrôle d'accès administrateur.
- Faire respecter les transitions documentaires côté serveur et enregistrer
  approbateur, date et version publiée.
- Relier chaque parcours à un critère `AC-*` et à une preuve de recette.

## 9. Lots réalisés

1. Restaurer le CDC détaillé et la matrice de critères dans le dépôt.
2. Unifier le contrat de sécurité et le flux de confirmation de maintenance.
3. Construire le squelette réel des onze sections Paramètres.
4. Finaliser Général et Apparence avec notification active et import de fichiers.
5. Livrer Contexte et Directives avec historique et restauration.
6. Livrer Mémoire avec recherche et gouvernance.
7. Achever Fournisseurs IA et Accès avec tests de connexion et états.
8. Livrer Outils et capacités avec permissions et audit d'utilisation.
9. Achever le volet Agents de bout en bout.
10. Renforcer le workflow documentaire et la citation RAG dans le chat.
11. Livrer Système, puis étendre les actions YunoHost par cas d'usage.
12. Livrer le centre Sauvegardes et ses opérations confirmées.
13. Livrer l'assistant de premier démarrage et le diagnostic final.
14. Exécuter la recette complète du paquet : installation, mise à jour,
    sauvegarde, restauration, permissions, parcours et régression.

## 10. Décision de diffusion

La couverture du CDC 2.0 est suffisante pour publier le paquet YunoHost 35 dans
le catalogue ARCenal stable. La recette serveur décrite dans la matrice reste
le contrôle d’exploitation obligatoire après installation ou mise à niveau.
