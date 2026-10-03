# État du projet ARCenal Agent

## LOT 10 — recette Preview et résilience LLM

- Date : 2026-10-03 ; version serveur `0.21.0-arcenal35`, paquet
  `0.21.0~ynh53`, source `ff93c4c59f` sur le canal preview.
- Verdict : `HARDENING REQUIRED`. Le rapport factuel est
  `docs/validation/LOT10_PREVIEW_ACCEPTANCE.md`.
- Gemini et OpenRouter répondent réellement en HTTP 200. Le repli 429, 503 et
  timeout est validé localement, ainsi que l'interdiction de repli pour les
  erreurs d'authentification et de configuration.
- Un défaut HIGH de classification des erreurs fournisseur est corrigé
  localement, mais reste non publié et non recetté sur YunoHost.
- Le redémarrage contrôlé conserve configuration, agents, conversations et
  secrets. Les services, permissions 0700/0600, UMask 0077 et journaux sont
  conformes ; dix lectures simultanées répondent HTTP 200 sans verrou SQLite.
- Validation : Ruff et ESLint sans erreur, `ty`, TypeScript et build réussis,
  242 tests Python ARCenal, 463 tests frontend, 20 tests Python et 9 scripts du
  paquet, 13 tests catalogue. ShellCheck reste indisponible.
- Restent à prouver : parcours navigateur, changement réel de modèle,
  automatisations, versioning LDA, SilverBullet, mémoire de recette, action et
  refus broker, puis cycle paquet sur instance jetable.
- Aucun commit, tag, push ou changement de catalogue n'a été effectué. Le
  fichier utilisateur `contributors/emails/agent@Agents-Mac-mini.local` reste
  exclu.

## LOT 09R final — recette YunoHost réelle

- Date : 2026-10-03 ; branche `arcenal`, source `v0.21.0-arcenal35`, paquet
  YunoHost `0.21.0~ynh53` installé depuis le catalogue preview.
- Verdict : `READY FOR LOT 10`. Rapport actualisé dans
  `docs/validation/LOT09R_PRODUCTION_COMPATIBILITY.md` ; aucun BLOCKER, HIGH ou
  MEDIUM ouvert.
- Le harnais d’ARC est en mode FIXED sur `hermes-current`, fournisseur Gemini,
  seul modèle actif classé `admin` lors de la recette. Le routage résout
  `gemini-3-flash-preview` sans modèle global porté par le fournisseur.
- Recette serveur : sauvegarde YunoHost créée, service ARCenal seul redémarré,
  backend `arc`, migration complète, coffre prêt, persistance prouvée, UMask
  `0077`, données sensibles `0700/0600` et aucune fuite des deux secrets réels
  recherchés dans le journal ou l’audit.
- Une requête ARC corrélée traverse réellement Agent Manager, Context Builder,
  RAG, Enterprise Memory, ARC Frugal, Model Router et Gemini. Une requête ATS
  réelle sélectionne sa source recrutement sans exposer la source finance.
  OpenRouter répond HTTP 200 sur un modèle gratuit. Toutes les sondes ont été
  intégralement nettoyées.
- Charge légère : dix réponses HTTP 200 simultanées en 2,6 à 7,4 ms, sans
  alerte ni blocage SQLite. SQLite 3.40.1 reste une observation LOW, compensée
  par le repli automatique en `journal_mode=DELETE` ; les bases répondent `ok`.
- Publication : source `ff93c4c59f4307274163a264a94e44473b0ca2d0`,
  paquet `b1e10a61bff97d7c6d06afbdeb6f4bb4b568d92a`, catalogue preview
  `9768e38`.
- Validation courante : ESLint sans erreur, TypeScript Web et dashboard, 131
  tests Python ARC ciblés, Ruff/Bash/compilation et 20 tests package, Ruff/
  compilation et 13 tests catalogue. `git diff --check` requis avant commit.
- Le canal stable reste inchangé. Les fichiers générés `__pycache__` et le
  fichier utilisateur `contributors/emails/agent@Agents-Mac-mini.local`
  restent exclus des commits.

## Fournisseur Codex — connexion par lien d’appareil

- Date : 2026-10-02 ; branche `arcenal`, source
  `v0.21.0-arcenal29` / paquet YunoHost `0.21.0~ynh47` publié en preview.
- Paramètres > Fournisseurs IA propose OpenAI Codex par code d’appareil. La
  connexion OAuth ne définit aucun modèle global : les modèles découverts sont
  affectés dans le harnais AUTO ou FIXED de chaque agent.
- L’interface distingue désormais l’authentification OpenAI de la finalisation
  ARC. Elle n’annonce « Configuré » qu’après synchronisation du catalogue et
  activation du fournisseur ; un échec reste reprenable avec « À finaliser ».
- Un verrou empêche les doubles synchronisations lors d’un re-rendu lent. Aucun
  fragment de jeton Codex n’est renvoyé au navigateur.
- Validation : Ruff et ESLint sans erreur, TypeScript et compilation Python
  réussis, 54 tests backend et 53 tests frontend ciblés, build de production,
  scripts du paquet et 20 tests Python YunoHost, 13 tests catalogue.
- Revue indépendante : aucun constat bloquant ou important après trois passes.
- Publication vérifiée : source `a7ddd9759112b3b7efee41439b23c9358645595a`,
  paquet `9c9ff6044d0c4585b62b349425f6958a9d84d79a`, catalogue preview
  `ad4e53e`. Le flux brut annonce `0.21.0~ynh47`.
- Le canal stable reste inchangé jusqu’à la recette réelle de la candidate.
- Le fichier utilisateur `contributors/emails/agent@Agents-Mac-mini.local`
  reste exclu du lot.

## Correctif — chat ARC natif et repli multi-fournisseurs

- Date : 2026-10-02 ; branche `arcenal`, source
  `v0.21.0-arcenal28` / paquet YunoHost `0.21.0~ynh46` publié en preview.
- Le chat ne passe plus directement par une session Hermes : il traverse ARC
  Core, l'Agent Manager, le Context Builder, le RAG, la mémoire d'entreprise et
  ARC Frugal avec le message courant.
- Le repli AUTO après une indisponibilité Gemini 503 est couvert jusqu'à
  OpenRouter. Le chat persiste ses conversations et reste utilisable après une
  erreur fournisseur.
- Le catalogue permet de déclarer le niveau de données autorisé par modèle ; un
  contexte d'administration n'est pas envoyé à un modèle limité aux données
  internes.
- Le paquet YunoHost cible ne demande plus de fournisseur, clé ou modèle global
  à l'installation. Le choix AUTO ou FIXED appartient à chaque agent.
- Validation locale : ESLint et Ruff sans erreur, TypeScript et compilation
  Python réussis, 217 tests Python ARCenal, 22 tests frontend impactés, build
  de production, 9 scripts YunoHost et 20 tests Python du paquet réussis.
- Rapport : `docs/validation/LOT09_PREPRODUCTION_AUDIT.md`.
- Publication vérifiée : source `f5166ac3c32389c726aae61b0741dc20e5af376b`,
  paquet `e7c4fd58868bb6cd788d7550e9e8a4f66f14f3f9`, catalogue preview
  `b1b94da`. Le flux brut annonce bien `0.21.0~ynh46`.
- La promotion stable reste bloquée jusqu'à la recette réelle de cette candidate
  installée depuis le canal preview.
- Le fichier utilisateur `contributors/emails/agent@Agents-Mac-mini.local`
  reste exclu du lot.

## Correctif — saturation temporaire des fournisseurs IA

- Date : 2026-10-02 ; branche `arcenal`, source `v0.21.0-arcenal26`, paquet
  YunoHost `0.21.0~ynh44` publié dans le canal `preview`.
- Les réponses HTTP 500, 502, 503 et 504 sont classées comme indisponibilité
  temporaire. En mode AUTO, ARC poursuit avec le prochain modèle autorisé ; en
  l’absence de repli, le chat affiche une erreur claire et reste utilisable.
- Les erreurs Gemini 503 ne restent plus bloquées sur « ARC analyse votre
  demande… ». Les secrets sont expurgés, y compris lorsqu’un fournisseur les
  sérialise dans un fragment JSON.
- Validation : Ruff et ESLint sans erreur, `ty`, TypeScript, compilation
  Python et build de production réussis ; 24 tests moteur et 17 tests de chat
  ciblés passent. La revue indépendante ne relève aucun BLOCKER, HIGH ou MEDIUM.
- Publication vérifiée : source `f396975074fad49cfc068781a6422b530ece5c00`,
  paquet `5fc0b7511cf942f1f7d2c3dd581be24c45c9bba8`, catalogue preview
  `1921ec6`. Le flux brut annonce bien `0.21.0~ynh44`.
- Le fichier utilisateur `contributors/emails/agent@Agents-Mac-mini.local`
  reste exclu du lot.

## Lot — Harnais par agent et tâches planifiées

- Date : 2026-10-02 ; branche `arcenal`, source `v0.21.0-arcenal25`, paquet
  YunoHost `0.21.0~ynh43` publié dans le canal `preview`.
- Les fournisseurs ne portent plus de modèle par défaut : ils conservent
  uniquement leur connexion, leur activation, leur URL et leur secret. Le
  choix AUTO ou FIXED appartient désormais à chaque agent.
- Chaque agent ARC Core dispose d’un harnais isolé : contexte, directives,
  mémoire, politique modèle, portées RAG, permissions, outils et autonomie.
  Les profils spécialisés disposent des mêmes paramètres dans leur répertoire.
- Les anciens fichiers Markdown globaux sont migrés une seule fois vers le
  harnais d’ARC. Les sources historiques sont conservées sans rester injectées
  globalement ; un fichier trop long est borné dans le paramètre sans perte de
  sa source complète. L’ancienne API globale `managed-files` n’est plus montée.
- Les onglets globaux Contexte, Mémoire et Directives sont retirés des
  paramètres. Un espace `Tâches planifiées` est ajouté entre ARC et Agents pour
  créer, lister, suspendre, reprendre, archiver ou supprimer des automatisations
  planifiées ou déclenchées, formulées en langage naturel.
- Validation : Ruff et ESLint sans erreur, `ty` ciblé, TypeScript, compilation
  Python et build de production réussis ; les 241 tests Python ARCenal et les
  445 tests frontend passent.
- Publication vérifiée : source `3e97eed68bb882a56f0450d52250553a5b1f8da2`,
  paquet `39bc4e8e746df95f324b565e98a5fba400e942c2`, catalogue preview
  `f14b6a0`. Aucun déploiement serveur n’a été déclenché.
- Le fichier utilisateur `contributors/emails/agent@Agents-Mac-mini.local`
  reste exclu du lot.

## LOT 09.1 — Catalogue modèles et contraste du chat

- Date : 2026-10-02 ; branche `arcenal`, candidate
  `v0.21.0-arcenal24` / paquet cible `0.21.0~ynh42`.
- Le Model Registry existant redevient la source de vérité visible. La
  découverte fournisseur normalise les modèles et conserve leur origine et
  leur disponibilité sans inventer les métadonnées inconnues.
- L'Agent Manager crée et modifie des agents avec une politique AUTO ou FIXED.
  FIXED exige un modèle concret, activé et compatible ; `local_only` interdit
  toujours un modèle distant. ARC Frugal conserve l'ordre déterministe, cache,
  workflow puis LLM.
- Le quota Gemini est distinct d'une authentification invalide. Un 429 termine
  l'attente, affiche un message expurgé et laisse le chat réutilisable.
- La bulle utilisateur et son Markdown utilisent la paire sémantique
  `--arc-primary` / `--arc-primary-text`, calculée selon la dominante en clair
  comme en sombre.
- Validation locale : Ruff, ESLint sans erreur, `ty`, TypeScript, compilation
  Python et build passent ; 237 tests Python ARCenal, 437 tests frontend,
  9 scénarios YunoHost, 20 tests broker/socket et 13 tests catalogue passent.
- Rapport : `docs/validation/LOT09_1_MODEL_CATALOGUE.md`.
- Prochaine étape : publier uniquement en preview, installer ynh42 par la voie
  YunoHost normale et reprendre la recette Lot 09R finale.
- Le fichier utilisateur `contributors/emails/agent@Agents-Mac-mini.local`
  reste exclu de tous les commits.

## LOT 09R — Recette de compatibilité de production

- Date : 2026-10-01 ; branche `arcenal`, version corrective
  `v0.21.0-arcenal23` publiée.
- État : le paquet Lot 09 `0.21.0~ynh38` est installé sur le serveur principal.
  Le chat a toutefois révélé une configuration Gemini incohérente : le
  fournisseur était `gemini` et le modèle littéral `auto`.
- Correctif publié : `arcenal22` synchronise le modèle choisi dans Paramètres
  avec le moteur conversationnel, refuse `auto` comme identifiant direct et
  couvre les parcours nominal, limite et erreur. `arcenal23` corrige également
  le test de connexion Gemini, qui envoyait à tort la clé comme jeton OAuth
  Bearer en plus du paramètre Google. Le paquet `0.21.0~ynh41` migre aussi
  l'ancienne combinaison `Gemini / auto` vers l'alias officiel
  `gemini-flash-latest` avant la copie vers le backend ARC. Il est publié en
  preview ; les validations et la publication GitHub sont réussies.
- État serveur prouvé par systemd : `0.21.0~ynh38`, `arcenal21`, révision
  `09214e609e8c20e8f998f911166a82b23c322c76`, service actif sur le port 9121.
  Le backend natif répond `arc`, mais le moteur reste sur Gemini / `auto` et le
  dernier test Gemini installé est `invalid` à cause du défaut désormais corrigé.
- Recette restante : mettre à niveau vers ynh41, tester Gemini, vérifier le
  modèle migré, ouvrir une nouvelle conversation et obtenir une réponse ARC
  réelle avant toute promotion stable.
- Observation serveur ultérieure : `arcenal.service` est actif et son processus
  a redémarré à 16:38 UTC. Le compte SSH non privilégié ne peut légitimement
  lire ni le manifeste YunoHost ni l'API locale protégée (HTTP 401) ; ce
  redémarrage ne prouve donc pas encore que ynh41 est installé.
- Preuves serveur : `/arcenal/` redirige vers SSOwat ; un faux en-tête
  `Remote-User` ne contourne pas l'authentification ; dix requêtes simultanées
  répondent sans erreur entre 66,5 et 79,8 ms. Les services ARCenal sont actifs,
  mais le bundle déployé ne contient pas l'API native `/configuration/v1` et les
  UMask observés sont `0022`, `0007`, `0022` au lieu de `0077`.
- Validation locale : Ruff, ESLint sans erreur, Bash, `ty` ciblé, TypeScript,
  compilation Python et build réussis ; 216 tests Python ARC, 423 tests Web,
  9 scénarios YunoHost et 16 tests broker réussissent.
- Rapport : `docs/validation/LOT09R_PRODUCTION_COMPATIBILITY.md`.
- Verdict courant : `LOT 09 HARDENING REQUIRED` ; le Lot 09 doit d'abord être
  réellement déployé avant restart, persistance, coffre, logs, ARC et ATS.
- Aucun commit Lot 09R : la condition « recette terminée » n'est pas remplie.
- Le fichier utilisateur `contributors/emails/agent@Agents-Mac-mini.local`
  reste explicitement exclu de tout futur commit.

## LOT 07B — Frontières YunoHost et autonomie progressive

- État : audit, simplification et contrôles locaux réalisés.
- YunoHost reste standard : aucun patch du cœur, de SSOwat, de Nginx global ou
  du catalogue officiel n’est requis par le paquet.
- Une mutation globale évitable a été retirée : `www-data` n’est plus ajouté à
  un groupe ARCenal ; le socket de contrôle utilise directement son groupe.
- Les frontières YunoHost, dépendances Hermes et dépendances techniques sont
  cartographiées. Une baseline locale mesure démarrage, RAM, CPU et tailles.
- Validation : Ruff et ESLint passent sans erreur nouvelle, typage ciblé,
  compilation Python, TypeScript et build passent ; 176 tests Python ARC, 421
  tests web, 9 scénarios shell YunoHost et 16 tests broker réussissent.
- Test principal sûr : l’accès HTTP anonyme à `/arcenal/` est redirigé par
  SSOwat vers `/yunohost/sso` ; aucune mutation distante n’a été effectuée.
- Les essais destructifs restent interdits sur le serveur principal ; leur
  statut est `NON TESTÉ — INSTANCE JETABLE REQUISE`.
- Publication GitHub : interdite sans autorisation explicite.

## LOT 07 — Hardening et recette YunoHost

- État : hardening local engagé ; recette YunoHost réelle bloquée par l'absence
  d'une instance dédiée.
- Défaut corrigé : les directives longues ne font plus disparaître une section
  entière du prompt ARC ; les trois sections restent sous les budgets Hermes et
  signalent explicitement les extraits bornés.
- Paquet durci localement : headers secondaires d'identité neutralisés par
  Nginx, permissions persistantes réappliquées, `UMask=0077`, remplacement
  complet des sources et réenregistrement du service après restauration.
- Livrables de recette créés : baseline préinstallation, jeu de données témoin,
  runbook, réponse aux incidents et matrice YunoHost.
- Validation locale : Ruff, typage ciblé, compilation Python, TypeScript et
  build réussis ; 176 tests Python ARC, 421 tests web, 8 scénarios shell du
  paquet et 16 tests du broker réussissent. La revue finale a aussi corrigé un
  retrait qui omettait trois des quatre fichiers de directives dans le prompt.
- Décision actuelle : `HARDENING REQUIRED` tant qu'installation, upgrade,
  restart, reboot, SSO, backup et restore ne sont pas réellement éprouvés.
- Publication GitHub : interdite sans autorisation explicite.

## LOT 06 — Préproduction multi-fournisseurs

- État : implémenté et validé localement ; intégré comme prérequis du lot 07.
- Décision FRUGAL-001 : ordre déterministe, cache, workflow validé, modèle routé.
- Décision FRUGAL-002 : aucune économie affichée sans baseline LLM mesurée.
- Décision PROVIDER-001 : capacité, modèle et fournisseur restent trois contrats indépendants.
- Décision PROVIDER-002 : OpenRouter reste interchangeable ; Ollama, OpenAI, Gemini, Anthropic, vLLM et les endpoints compatibles utilisent le même registre.
- Preuve réelle : une génération `openrouter/free` via le Provider Adapter, 1 tentative, 13 888 tokens d'entrée, 2 tokens de sortie, coût rapporté nul, 5 287,29 ms.
- YunoHost : packaging SSOwat et rotation des secrets préparé dans le dépôt séparé ; recette réelle non effectuée faute d'instance de test accessible pour cette révision locale.
- Validation : Ruff, ESLint, ty ciblé, TypeScript, compilation Python et build réussis ; 173 tests Python ARCenal, 421 tests frontend, 7 scénarios shell YunoHost et 16 tests du broker réussis.
- Publication GitHub : interdite sans autorisation explicite.

Dernière mise à jour : 2026-10-02

Branche : `arcenal`

## Objectif courant

Maintenir YunoHost standard, rendre le paquet ARC réversible et non intrusif,
mesurer son empreinte puis préparer l’extraction incrémentale du runtime Hermes
derrière les interfaces ARC existantes.

## État observé

- L'ancien tableau de pilotage est remplacé dans la navigation par trois
  espaces ARC, Agents et RAG & LDA ; le contrôle visuel est validé.
- Le plugin `arcenal-supervisor` expose l’état système, les rapports et trois
  réparations strictement autorisées, ainsi qu’un pont local en lecture vers
  les données natives YunoHost.
- Le paquet natif est maintenu séparément dans `arcenal_ynh`.
- AACP/1 est documenté, mais aucun connecteur applicatif n’est encore livré.
- Une modification utilisateur hors périmètre existe dans
  `contributors/emails/agent@agents-Mac-mini.local` et doit rester intacte.

## Décisions actives

- Hermes reste le moteur technique interne ; ARC est l’identité publique et le
  comportement spécialisé.
- Les adaptations ARC doivent utiliser les extensions et plugins avant toute
  modification du cœur commun.
- Les opérations destructives ou sensibles exigent une confirmation explicite
  de l’administrateur dans la conversation en cours.
- Les applications tierces suivront AACP/1 lorsqu’un connecteur sera développé.
- Le volet RAG repose sur un corpus Markdown portable, un wiki documentaire et
  une LDA calculée à partir des seules versions au statut `Applicable`.
- SilverBullet est retenu comme coffre éditorial et interface de connaissances
  liée ; Nextcloud est exclu du périmètre RAG. ARC conserve l'index, les ACL,
  les citations, le workflow LDA et la publication du wiki salarié.
- SilverBullet reste non rebrandé pour le moment ; son thème et son interface
  d'origine sont conservés afin de limiter l'intégration à ses fonctions et à
  son API.
- Les révisions documentaires suivent le cycle Brouillon, En révision, À
  approuver, Applicable, Archivé ; ARC peut proposer une révision, mais le
  workflow d'approbation contrôle sa publication.
- Le socle documentaire intégré utilise Markdown, FastAPI et React ; il reprend
  les liens et liens entrants d'Obsidian sans ajouter de service externe.
- Les clés des fournisseurs sont saisies uniquement dans Paramètres, stockées
  par le mécanisme de secrets existant et ne sont jamais renvoyées par l'API ou
  l'interface.
- Les comptes métier et jetons API sont séparés de leurs métadonnées : les
  secrets restent dans `.env`, tandis que le catalogue d’accès ne fournit à ARC
  que le service, le login, le périmètre et le nom de variable à utiliser.

## Travail en cours

Le lot 07 durcit actuellement le paquet et la frontière de prompt avant recette
réelle. ARC Frugal reste le socle validé du lot 06 : il arbitre entre exécution
déterministe, cache, workflow gouverné et LLM routé au travers d'un registre de
fournisseurs et d'un adaptateur commun. Le lot 04 reste intégré : la mémoire d'entreprise est une
collection SQLite gouvernée, distincte du corpus officiel mais interrogée par
le même RAG après contrôle des ACL. Les faits, décisions, personnes, projets,
règles et préférences conservent provenance, confidentialité, scopes, durée de
conservation, relations et historique de correction. Les mémoires expirées,
archivées ou supprimées quittent l'index dérivé reconstruisible. La page
Paramètres > Mémoire fournit recherche, filtres, fiche, métriques, création,
correction, archivage, réactivation, expiration et droit à l'oubli. Les lots 01
à 04 et leurs quatre commits restent inchangés ; aucun push n'a été effectué.

- L'architecture de sécurité a été validée par l'utilisateur le 2026-09-28 :
  YunoHost reste l'unique autorité d'identité et ARC ne crée pas de second mot
  de passe ; les actions privilégiées passent par un broker séparé.
- La fondation des lots 0 à 6 est implémentée. Le catalogue de risques et
  les niveaux d'autorisation 0 à 3 refusent par défaut toute action inconnue.
- Un jeu d'outils `arcenal-admin` retire terminal, processus, fichiers
  arbitraires, exécution de code, délégation et cron du superviseur installé
  sur YunoHost.
- Le paquet remplace le helper `sudoers` par trois frontières : un socket de
  lecture pour le moteur, une API de contrôle identifiée par SSOwat et un
  socket privilégié accessible uniquement à l'utilisateur de contrôle.
- Les actions de niveau 3 utilisent une confirmation à usage unique, liée à
  l'administrateur, l'action et la cible, avec une expiration de cinq minutes.
- Le journal d'audit est expurgé, synchronisé et chaîné par empreinte. Il est
  conservé dans `/var/lib/arcenal-control` pour être sauvegardé séparément.
- Le menu Paramètres adopte une navigation interne Apparence, Fournisseurs IA,
  Accès et Sécurité. Les libellés n'annoncent plus d'administration complète
  sans confirmation.

- L’identité et les règles opérationnelles d’ARC sont injectées dans le prompt
  système par le plugin `arcenal-supervisor`, après la mémoire de session.
- Les tests vérifient la spécialisation et les cinq outils de supervision et
  de recherche documentaire exposés à ARC.
- Le dashboard propose les trois opérations de maintenance autorisées, impose
  une confirmation visible et transmet uniquement des identifiants bornés.
- L’API rejette les opérations inconnues, les services hors liste et les
  requêtes qui ne portent pas la confirmation administrateur.
- La livraison applicative `v0.21.0-arcenal19` et le paquet `arcenal_ynh`
  `0.21.0~ynh34` sont publiés sur GitHub. Les canaux développement,
  prévisualisation et stable référencent la révision
  `d0e23cf8c70c53d65a3c2222f29c9115fdd513f2`.
- Le paquet reconstruit proprement le code et les dépendances pendant
  l'upgrade, réinstalle `uv` si nécessaire et accepte la restauration
  `BACKUP_CORE_ONLY` sans masquer l'erreur initiale.
- Le build web de production exclut désormais les fichiers de test ; il réussit
  sur YunoHost sans installer `@testing-library/react`.
- Le volet ARC remplace le terminal TUI par un chat web natif relié à la
  passerelle conversationnelle Hermes. Il gère l'historique, le flux de réponse,
  l'arrêt d'une action et les validations administrateur.
- Le menu Paramètres conserve simultanément les accès OpenRouter, OpenAI,
  Anthropic, Gemini, Ollama et les clés personnalisées. Il permet de sélectionner
  le modèle principal et de choisir une autonomie manuelle, encadrée ou étendue.
- Paramètres contient désormais un coffre de comptes et d’API métier, avec une
  autonomie propre à chaque service, ainsi qu’un commutateur clair, sombre ou
  synchronisé sur le système.
- L'interface ARC reprend le thème Gratitude : fond crème et vert clair, cartes
  blanches arrondies, ombres chaudes, typographie Inter et accent terre cuite.
- Le coffre Markdown persistant, la recherche plein texte pour ARC, les liens
  entrants, l'historique, la LDA calculée et le wiki en lecture sont
  implémentés dans le plugin `arcenal-supervisor` et l'interface React.
- La LDA possède désormais son registre métier dédié avec les vues utilisables
  et archivées, les champs QSSERP, la recherche, les filtres, l'export CSV, la
  pagination, l'ouverture des fiches et l'archivage avec confirmation.
- Le formulaire de création documentaire collecte la dénomination, l'activité,
  la numérotation, la nature, la date de validation, la révision et le motif,
  tout en conservant le document source original dans un espace privé. Les
  formats PDF, DOCX, ODT, TXT et Markdown sont acceptés jusqu’à 20 Mio.
- L’historique visible depuis le chat permet maintenant d’archiver ou de
  supprimer une conversation après confirmation.
- La façade ARC ne rend plus la barre latérale technique Hermes. Le bandeau
  principal récupère le logo et le nom de l’organisation depuis la
  personnalisation publique YunoHost, avec le logo ARCenal en secours.
- Le volet ARC permet d’archiver la conversation active après confirmation et
  ouvre immédiatement une nouvelle conversation ; la mention « Moteur Hermes »
  a disparu de la carte de supervision, tandis que « by Hermes » reste discret
  dans le bandeau principal.
- Le wiki dispose d'une route séparée `/wiki` qui ne charge pas la façade
  d'administration et n'expose que les versions `Applicable`.
- Le paquet YunoHost fixe l'administration au groupe `admins`
  et réserve au groupe `all_users` la route du wiki et ses API de lecture.
- Le CDC approuvé est formalisé dans `docs/arcenal-product-cdc.md`.
- Le CDC détaillé retrouvé dans la demande utilisateur est maintenant conservé
  dans `docs/arcenal-product-cdc-v2.md`. L'audit
  `docs/arcenal-product-audit.md` classe chaque domaine en existant, partiel,
  absent ou à refactoriser et remplace les affirmations générales de conformité.
- Le premier lot de réalisation validé ajoute les panneaux Général et Apparence
  sans créer d'onglet factice : identité d'ARC, organisation, langue, fuseau,
  adresse de notification, versions serveur, couleurs, logo, favicon et aperçu.
  Le bandeau reprend immédiatement ces réglages tout en conservant la
  personnalisation publique YunoHost comme valeur de secours.
- Le lot Contexte et Directives ajoute un stockage Markdown à liste blanche,
  l'auteur et la date de modification, un aperçu, un historique atomique et la
  restauration confirmée. `CONTEXT.md` est interrogeable par ARC avec des
  extraits bornés et les quatre directives sont figées dans chaque nouvelle
  session afin qu'une modification ne change pas silencieusement un échange en
  cours.
- Le lot Mémoire expose `MEMORY.md` sous forme d’entrées durables : consultation,
  recherche, ajout, modification, suppression confirmée, historique et
  restauration. ARC dispose d’un outil de recherche dédié et reçoit un extrait
  borné de la mémoire au début de chaque nouvelle session. Le format interdit
  l’injection de faux titres d’entrée.
- Le lot Connexions complète les fournisseurs IA et le coffre d’accès. Chaque
  fournisseur peut être activé, testé, associé à un modèle principal et à un
  modèle secondaire ; les API compatibles OpenAI acceptent une adresse privée
  contrôlée. Les résultats expurgés sont horodatés et persistés sans secret.
- Les accès métier déclarent désormais leurs permissions, leur autonomie et
  leur état. Ils peuvent être testés, activés ou désactivés ; seuls les accès
  actifs sont présentés aux outils d’ARC, sans valeur de mot de passe ou de
  jeton.
- Le panneau Outils inventorie séparément les capacités ARCenal et les
  ensembles hérités de Hermes. Il affiche permission, risque, confirmation,
  disponibilité et dernière utilisation ; les ensembles Hermes configurables
  peuvent être activés, tandis que les outils ARC critiques restent protégés.
- Un hook officiel `post_tool_call` journalise le nom, le résultat synthétique,
  la durée et le compteur d’utilisation de chaque outil. Aucun argument ni
  contenu de résultat n’est conservé ; l’écriture atomique est sérialisée.
- Le lot 01 introduit ARC Core, un Agent Manager générique, un Context Builder
  minimal et un registre atomique sauvegardable. ARC et Agent ATS partagent le
  moteur Hermes, la politique globale, les contrôles et l'audit.
- L'API `POST /api/v1/agents/{agent_id}/query` authentifie l'application par un
  secret dédié, conserve séparément l'utilisateur éventuel et refuse les
  agents inconnus, désactivés ou hors périmètre sans repli privilégié.
- La page Agents affiche le registre ARC Core et ouvre une fiche persistante
  permettant uniquement de modifier l'état, l'autonomie et la politique de
  modèle. Les profils Hermes existants restent disponibles séparément.
- Le lot 02 ajoute un index documentaire JSON dérivé et reconstructible, un
  chunking par sections Markdown et un reranking lexical déterministe.
- Le Context Builder construit un `ContextPlan` serveur et applique avant la
  recherche les statuts, scopes, ACL applicatives, permissions et niveaux de
  confidentialité. Les citations de l'API proviennent exclusivement des
  chunks retenus.
- Le volet RAG & LDA expose les documents et chunks indexés, la date, les
  erreurs et une reconstruction confirmée réservée à l'identité YunoHost.

## Validation prévue

## Lot 0 — audit, stabilisation et préparation (2026-09-30)

- La cartographie factuelle du produit, du flux IA, des connaissances, des
  agents, du RAG et de la LDA est consignée dans `docs/architecture/`.
- Le contrat de thème ARC est centralisé dans `web/src/arcenal-theme.css` et
  fournit les jetons sémantiques partagés par la façade et les plugins.
- Le dashboard du superviseur ne conserve plus de palette autonome : sa feuille
  source est versionnée, copiée pendant le build et consomme le contrat global.
- Le chat utilise le composant Markdown sécurisé de la façade pour rendre les
  réponses, les liens, le code et les citations selon le même thème.
- Le changement de couleur dominante alimente les jetons primaire et action,
  avec calcul d'une couleur de texte contrastée.
- L'instrumentation existante des appels IA est jugée réutilisable : provider,
  modèle, tokens normalisés, cache, durée, appels API et coût estimé sont déjà
  persistés. Aucune seconde chaîne de mesure n'a été ajoutée.
- La cible ARC Core, l'interface future de service d'agents, le plan de
  migration, la baseline et la dette technique sont documentés sans amorcer
  les lots fonctionnels suivants.
- Validation web finale : ESLint sans erreur (28 avertissements historiques),
  TypeScript réussi, 60 fichiers et 404 tests Vitest réussis, build de
  production réussi.
- La réserve Python est levée : `.venv` utilise Python 3.11.15 et les
  dépendances de développement déclarées. Les 108 tests du lot 0 réussissent.

## Lot 01 — ARC Core et Agent Manager (2026-09-30)

- Ruff réussit ; ESLint réussit sans erreur avec 28 avertissements historiques.
- ARC Core passe `ty` et l'interface passe TypeScript.
- Les 118 tests Python ARCenal et les 406 tests Vitest réussissent.
- Le build Vite de production, la compilation Python et `git diff --check`
  réussissent.
- La suite amont exhaustive a été lancée mais interrompue à 3,2 % : plusieurs
  tests optionnels exigent les extras `acp` et `anthropic`, absents de l'extra
  `dev`. Ce constat n'affecte pas les 118 tests canoniques ARCenal.

## Lot 02 — RAG central (2026-09-30)

- Réalisation locale terminée ; aucune publication distante.
- Le `ContextPlan` est construit côté serveur, strict, profondément immuable
  pour ses filtres, et borne statuts, sources, confidentialité et budget.
- Les ACL cumulatives sont appliquées avant la recherche par application,
  agent, utilisateur, permission, scope, statut et niveau de confidentialité.
- L'index JSON dérivé est atomique, déterministe et reconstruisible depuis le
  coffre Markdown ; la reconstruction est confirmée et réservée à un acteur
  YunoHost authentifié.
- La recherche lexicale, le reranking déterministe, les budgets, les citations
  structurées, l'audit sans contenu documentaire et les métriques sont actifs.
- La façade RAG affiche documents, fragments, erreurs et date d'indexation,
  puis permet une reconstruction explicitement confirmée.
- Le scénario ATS vérifie la version applicable, l'exclusion d'une version
  archivée, le cloisonnement d'un document comptable restreint et l'absence de
  citation quand la recherche est vide.
- Validation finale : Ruff et ESLint réussissent sans erreur ; les 28
  avertissements ESLint appartiennent au socle connu, dont le chargement
  asynchrone déjà employé par les pages.
- `ty` et TypeScript réussissent. Les 94 tests Python ARCenal et les 407 tests
  Vitest réussissent. Le build Vite de production et `git diff --check`
  réussissent.

## Lot 04 — mémoire d'entreprise gouvernée (2026-09-30)

- SQLite conserve la source canonique et l'historique ; l'index JSON reste
  dérivé et est reconstruit après chaque mutation via l'API.
- Le Context Builder distingue `Official Knowledge` et `Enterprise Memory` ;
  les sources officielles restent prioritaires en cas de contradiction.
- Les ACL cumulatives précèdent le retrieval. Le scénario ATS exclut une
  mémoire comptable confidentielle et accepte une mémoire de recrutement.
- Ruff et `ty` ciblé réussissent ; ESLint réussit sans erreur avec les 28
  avertissements historiques du socle. TypeScript, compilation Python et build
  Vite réussissent.
- Les 117 tests Python ARCenal et les 416 tests Vitest réussissent. La page
  Mémoire a été inspectée sur le build en thème sombre ; l'absence du backend
  dans la prévisualisation statique produit uniquement les erreurs réseau
  attendues. `git diff --check` réussit.

Résultats intermédiaires du 2026-09-28 : ESLint réussit sans erreur avec les
29 avertissements déjà présents dans le socle ; TypeScript réussit. Les
19 tests unitaires de politique, identité, confirmation, audit et surface
d'outils, les 9 tests du broker, les 53 tests Vitest ARC et les six tests shell
YunoHost réussissent. Le build web de production réussit. L'installation réelle du
nouveau découpage systemd reste à valider sur la machine YunoHost de recette.

Résultats du 2026-09-24 : Ruff et ESLint réussis sans erreur, vérification
TypeScript et compilation Python réussies. Pour le lot OpenRouter, 3 tests
Python isolés et 20 tests Vitest ciblés réussissent ; les tests du paquet
YunoHost et les 9 tests du catalogue réussissent également. Le build de
production Vite réussit et la page Paramètres a été contrôlée visuellement.
Le test de non-régression de l'upgrade et de sa restauration réussit. Le build
YunoHost a aussi été reproduit sans la dépendance de test absente du serveur.
Le chat ARC et le build web passent leur vérification TypeScript. Les 22 tests
Vitest ciblés, les quatre tests du paquet et les 9 tests du catalogue réussissent.
Les avertissements ESLint restants proviennent du socle Hermes préexistant. Les
tests Python du plugin n'ont pas été relancés localement faute de `pytest` dans
l'environnement disponible pour le lot précédent.
Le registre LDA passe ESLint sans nouvelle erreur, la vérification TypeScript,
13 tests Vitest ciblés, la compilation Python et le build Vite de production.
Son affichage et son formulaire de création ont été contrôlés dans le navigateur.
Le paquet ynh31 passe les six tests shell et le catalogue système ses 9 tests
Python. Les promotions development, preview et stable ainsi que la publication
GitHub Pages sont réussies ; les deux flux publics annoncent bien ynh31.
Le lot suivant passe ESLint sans erreur nouvelle, TypeScript, 27 tests Vitest,
la compilation Python, le test shell du pont YunoHost et le build Vite. Les
thèmes clair et système ainsi que le coffre d’accès ont été contrôlés dans le
navigateur. La suite Python n’a pas démarré sur le Mac faute de module `pytest`.
Le lot d’épuration de l’interface passe ESLint sans erreur nouvelle, TypeScript,
la compilation du module ARC, 11 tests Vitest ciblés et le build Vite de
production. Le bandeau sans barre latérale a été contrôlé dans le navigateur ;
le chat complet nécessite la passerelle du serveur YunoHost pour son contrôle
visuel final.
Le paquet ynh32 passe la validation Bash, le chargement TOML et ses six tests
shell. Le catalogue système passe la compilation Python, ses 9 tests unitaires,
la régénération exacte des trois canaux et les promotions GitHub jusqu’au canal
stable. Les flux publics direct et stable annoncent bien ynh32.
Le paquet ynh33 passe les contrôles locaux du broker et du paquet. Les
promotions development, preview et stable réussissent sur GitHub ; les neuf
tests du catalogue et sa publication Pages réussissent. Les flux stable brut
et Pages annoncent bien ynh33.
Le paquet ynh34 supprime la course au démarrage du socket de contrôle : le
service crée désormais directement le socket avec le groupe attendu par Nginx,
sans commande différée fragile. La sauvegarde cœur inclut aussi les unités
systemd et la configuration Nginx afin qu'une restauration après échec dispose
toujours de fichiers restaurables. Les neuf tests du broker, les six tests shell
du paquet et les treize tests du catalogue réussissent. Les promotions ciblées
development, preview et stable, puis la publication Pages réussissent ; les
flux publics brut et Pages annoncent bien ynh34.
Le lot Général et Apparence passe ESLint sans erreur nouvelle, TypeScript, les
349 tests Vitest et le build Vite de production. Les quatre scénarios backend
ajoutés passent avec le Python Hermes ; le lanceur canonique reste indisponible
localement faute de `pytest`, sans installation implicite de dépendance.
Le lot Contexte et Directives passe ESLint sans erreur nouvelle, TypeScript,
les 354 tests Vitest, la compilation Python et le build Vite de production. La
suite Python ciblée ne peut pas être chargée sur ce Mac, car FastAPI et pytest
ne sont présents dans aucun environnement existant ; aucune dépendance n'a été
installée implicitement.
Le panneau Mémoire a été contrôlé visuellement en thème sombre avec des données
nominales ; sa hiérarchie, ses cartes, son formulaire et son historique sont
lisibles dans la façade ARC sans réintroduire l’interface Hermes.
Le lot passe ESLint sans erreur nouvelle, TypeScript, les 360 tests Vitest, la
compilation Python et le build Vite de production.
Le lot Connexions passe ESLint sans erreur nouvelle, TypeScript, les 368 tests
Vitest, la compilation Python et le build Vite de production. Les panneaux
Fournisseurs IA et Accès ont été contrôlés visuellement en thème sombre. Les
tests Python ciblés sont présents mais restent non exécutables sur ce Mac faute
de FastAPI, Pydantic et pytest installés ; aucune dépendance n’a été ajoutée.
Le lot Outils passe la vérification TypeScript, 25 tests Vitest ciblés, quatre
tests Python autonomes et la compilation Python. Le panneau a été contrôlé en
thème sombre avec des capacités ARCenal protégées et des capacités Hermes
activables.

## Étape suivante pressentie

## Lot 08 — ARC Native Runtime, tranche Configuration & Vault (2026-10-01)

- `ArcConfigStore`, `ArcVault`, leurs backends natifs et
  `ArcRuntimeConfiguration` constituent désormais la frontière de
  configuration du produit.
- La migration HERMES est en lecture seule, idempotente et conserve la valeur
  ARC en cas de conflit explicite.
- Les imports directs de `hermes_cli.config` dans ARC passent de sept à un,
  localisé dans `HermesConfigAdapter`.
- ARC Frugal, les fournisseurs, les accès métier, SilverBullet et le catalogue
  du chat utilisent la nouvelle frontière sans ajouter de dépendance.
- Validation : Ruff, typage ciblé, compilation Python, 194 tests Python, ESLint sans erreur,
  TypeScript, 421 tests Vitest, build de production, 9 scénarios shell YunoHost
  et 16 tests du broker réussissent.
- Mesure locale : première réponse 1 s, repos 145 600 Kio, 145 808 Kio après
  dix lectures ; environnement Python et build web stables.
- Aucune publication, version ou release n’a été créée.

## Lot 09 — ARC Native Configuration Cutover (2026-10-01)

- ARC natif est le backend de configuration implicite ; HERMES n’est disponible
  qu’en mode legacy explicite, en lecture seule et visible dans le diagnostic.
- Général, Apparence, Fournisseurs, Accès, Autonomie et onboarding passent par
  l’API ARC Config/Vault sans réécriture de leur interface.
- La migration existante est non destructive, vérifiée, idempotente sur trois
  passages, conserve ARC en cas de conflit et ne journalise aucune valeur.
- Le paquet YunoHost déclenche cette migration pendant install, upgrade et
  restore, puis resserre les permissions en `0700/0600`.
- La frontière conversationnelle restante est documentée dans
  `HERMES_RUNTIME_BOUNDARY.md`; aucun runtime de remplacement n’a été commencé.
- Mesure locale : première réponse 1 s, 146 256 Kio au repos et 146 432 Kio
  après dix lectures ; tailles Python, web et plugin stables face au Lot 08.
- Aucune publication, version, release, dépendance, base ou service ajouté.

Proposition uniquement : Lot 10 — placer `_run_agent`, le gateway de streaming
et les sessions derrière l’interface minimale `ArcAgentRuntime`, en conservant
un adaptateur HERMES temporaire et sans dupliquer les composants ARC existants.
