# Audit de conformité ARCenal Agent

Date : 28 septembre 2026

Référence : [CDC détaillé 2.0](arcenal-product-cdc-v2.md)

Version auditée : branche `arcenal` au commit `e3b94f58c6`, application
`v0.21.0-arcenal19`, paquet YunoHost `0.21.0~ynh34`.

## 1. Architecture actuelle

- Le cœur Hermes fournit la conversation, les profils, fournisseurs, modèles,
  compétences, outils, mémoire, sessions et API web générales.
- La façade React ARC ajoute les routes ARC, Agents, RAG & LDA, Wiki et
  Paramètres, ainsi qu'un thème ARCenal sans barre latérale Hermes.
- Le plugin `arcenal-supervisor` injecte l'identité ARC, sept outils spécialisés,
  l'API documentaire, la supervision et trois opérations de maintenance.
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

Ces fonctions restent utiles, mais plusieurs écrans avancés Hermes ne sont pas
encore réorganisés dans les parcours métier ARC demandés.

## 3. Développements spécifiques ARC

- identité, prompt et outils ARC ;
- chat web rebrandé et historique archivable ou supprimable ;
- façade principale à trois volets et thème ARCenal ;
- création simple d'un profil agent ;
- coffre Markdown, pièces jointes, recherche, liens, historique, LDA, wiki et CSV ;
- saisie de plusieurs fournisseurs et choix du modèle principal ;
- coffre de comptes et API avec niveau d'autonomie ;
- supervision de ressources et services ;
- politique d'autorisation, confirmations à usage unique et audit chaîné ;
- broker root à catalogue fermé et pont YunoHost en lecture.

## 4. Intégration YunoHost

Le paquet v2 installe depuis une archive GitHub épinglée, construit l'interface,
crée les utilisateurs et groupes techniques, configure Nginx, SSOwat et trois
services systemd, puis sauvegarde les données et configurations essentielles.
L'administrateur est un utilisateur YunoHost existant. Il n'existe pas encore
de parcours complet de premier démarrage, d'identité de notification, de centre
de sauvegarde ou de diagnostic final visible.

## 5. Sécurité observée

Les fondations sont solides : refus par défaut, six actions cataloguées, quatre
niveaux, cibles bornées, séparation des identités, jetons de confirmation à
usage unique et audit expurgé. La couverture fonctionnelle reste étroite et le
centre de sécurité visible est absent. La façade de maintenance historique
possède encore un chemin de confirmation booléen distinct du flux renforcé ; il
doit être unifié avec l'API de contrôle.

## 6. Matrice CDC

| Domaine | État | Preuve et écart principal |
|---|---|---|
| Fork maintenable | PARTIEL | Plugin et paquet séparés, mais la stratégie de fusion amont n'est pas automatisée ni testée. |
| Installation native | PARTIEL | Paquet installable et actualisable ; premier démarrage et diagnostic final absents. |
| Administrateur YunoHost | EXISTANT | SSOwat et groupe `admins`, propriétaire sélectionné à l'installation. |
| Identité de notification | ABSENT | Aucun compte ou paramètre mail ARC dédié. |
| Trois volets principaux | EXISTANT | ARC, Agents et RAG & LDA sont les seules entrées métier. |
| Chat ARC | PARTIEL | Chat natif, historique et fournisseur ; recette complète diagnostic-action-vérification manquante. |
| Agents spécialisés | EXISTANT | Création et administration intégrées d’un profil isolé avec identité, mission, modèles principal et secondaire, compétences, outils et mémoire dédiée. |
| Connecteurs AACP/1 | PARTIEL | Contrat documenté, aucun connecteur actif conformément au périmètre ; la carte de feuille de route n'apporte pas de fonction. |
| Coffre Markdown | EXISTANT | Création, lecture, édition, recherche, liens, historique et pièces jointes présents. |
| Cycle documentaire | PARTIEL | Statuts et filtrage présents ; approbation nominative, transitions contrôlées et restauration UI manquent. |
| LDA | EXISTANT | Registre, filtres, archive, pagination et CSV présents. |
| Wiki | EXISTANT | Route séparée en lecture limitée aux documents applicables. |
| RAG traçable | PARTIEL | Outils de recherche et lecture présents ; preuve bout en bout de citation par le chat absente. |
| Paramètres Général | PARTIEL | Écran ARC, identité, langue, fuseau, adresse de notification et versions détectées ; l'envoi de notification reste à raccorder. |
| Paramètres Apparence | PARTIEL | Clair, sombre, système, couleurs, logo, favicon, nom et prévisualisation ; l'import de fichier local reste à ajouter. |
| Paramètres Contexte | EXISTANT | Éditeur Markdown, aperçu, auteur, date, historique, restauration confirmée et récupération ciblée de `CONTEXT.md`. |
| Paramètres Mémoire | EXISTANT | `MEMORY.md` dispose d’un parcours ARC de consultation, recherche, ajout, modification, suppression confirmée, historique et restauration. |
| Paramètres Directives | EXISTANT | Inventaire borné, édition, aperçu, historique et restauration de `AGENTS.md`, `RULES.md`, `SECURITY.md` et `TOOLS.md`, injectés dans les nouvelles sessions. |
| Fournisseurs IA | EXISTANT | OpenRouter, OpenAI, Anthropic, Mistral, Gemini, Ollama et API compatibles disposent d'une adresse contrôlée, d'un modèle principal et secondaire, d'une activation, d'un test réel et d'un état persistant expurgé. |
| Accès métier | EXISTANT | Comptes et API associent périmètre, permissions et autonomie ; ARC ne voit que les accès actifs, tandis que le test réel, l'état, la date et la désactivation restent gouvernés depuis Paramètres. |
| Outils et capacités | EXISTANT | L’inventaire distingue ARCenal et Hermes, expose état, permission, risque, confirmation et dernière utilisation ; les capacités Hermes configurables sont activables, les outils ARC critiques restent protégés. |
| Vue Système | PARTIEL | Ressources et cinq services ; applications, mises à jour, domaines, certificats, sauvegardes et journaux manquent. |
| Moteur de permissions | EXISTANT | Quatre niveaux, rôles, cibles et refus par défaut testés. |
| Passerelle privilégiée | PARTIEL | Séparée et fermée, mais seulement six actions et trois mutations. |
| Confirmation renforcée | PARTIEL | Jeton à usage unique présent ; présentation complète et unification de tous les chemins manquent. |
| Centre de sécurité | ABSENT | Audit backend présent, aucune vue administrateurs, rôles, sessions, confirmations ou événements. |
| Sauvegardes | PARTIEL | Scripts de sauvegarde/restauration ; aucun centre, état, déclenchement ou recette complète sur le serveur en ligne. |
| Premier démarrage | ABSENT | Pas d'assistant de vérification, identité, permissions et diagnostic. |
| Tests de conformité CDC | À REFACTORISER | Nombreux tests unitaires, mais aucune matrice AC ni recette de parcours complète. |

## 7. Risques techniques

1. Deux chemins de maintenance coexistent : l'API plugin et l'API de contrôle.
   Ils peuvent appliquer des règles de confirmation différentes.
2. La synchronisation d’un grand nombre de compétences ou d’outils effectue
   plusieurs écritures ; une interruption réseau peut laisser une spécialisation
   partiellement appliquée, explicitement signalée à l’administrateur.
3. Les paramètres promis sont dispersés dans les API Hermes ; les exposer sans
   couche métier ARC risquerait de réintroduire le tableau de bord technique.
4. La modification libre du frontmatter peut contourner le futur processus
   d'approbation documentaire si les transitions ne sont pas validées côté serveur.
5. Le catalogue privilégié est trop réduit pour le rôle d'administrateur
   YunoHost annoncé ; l'élargir sans schémas et vérifications serait dangereux.
6. Aucune recette installée ne prouve encore sauvegarde, restauration et mise à
   jour des nouvelles données fonctionnelles sur la cible en ligne.

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

## 9. Ordre exact recommandé

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
12. Livrer le centre Sécurité et le centre Sauvegardes.
13. Livrer l'assistant de premier démarrage et le diagnostic final.
14. Exécuter la recette complète du paquet : installation, mise à jour,
    sauvegarde, restauration, permissions, parcours et régression.

## 10. Décision de passage en réalisation

La prochaine modification structurelle doit commencer par les étapes 2 et 3.
Elle nécessite la validation de cette architecture conformément au CDC. Les
correctifs de sécurité ou de packaging restent autorisés indépendamment.
