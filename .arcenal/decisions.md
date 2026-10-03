# Décisions structurantes ARCenal Agent

## LLM-RESILIENCE-001 — Repli limité aux erreurs transitoires

- Date : 2026-10-03
- Décision : une nouvelle tentative peut traiter une réponse invalide, mais le
  passage à un autre fournisseur est limité à `rate_limited`, `timeout` et
  `unavailable`.
- Sécurité : les erreurs d'authentification, de configuration, de politique,
  d'ACL ou de secret absent restent explicites et n'autorisent aucun repli.
- Conséquence : une mauvaise clé ou un modèle inexistant ne peut plus être
  masqué par la réponse d'un autre fournisseur.

## SEC-001 — Identité administrateur

- Date : 2026-09-28
- Décision utilisateur : l'administrateur ARC est un administrateur YunoHost
  existant ; aucun second mot de passe ARC n'est créé.
- Conséquence : SSOwat protège l'interface et transmet l'identité à l'API de
  contrôle. L'utilisateur choisi à l'installation reçoit aussi le rôle
  `owner`, tandis que les autres membres de `admins` gardent le rôle
  administrateur.
- Réexamen : uniquement si ARCenal Système abandonne YunoHost comme autorité
  d'identité.

## SEC-002 — Séparation des privilèges

- Date : 2026-09-28
- Décision utilisateur : aucune action privilégiée ne doit être exécutée
  directement par Hermes ou son terminal.
- Décision technique : le moteur, l'API de contrôle et le broker root utilisent
  des identités et des sockets distincts. Nginx ne possède pas l'accès au
  socket root. Le moteur ne possède qu'un socket de lecture à catalogue fermé.
- Conséquence : une réparation proposée dans le chat doit être confirmée dans
  la surface ARC authentifiée avant transmission au broker.
- Réexamen : seulement après une revue de sécurité indépendante du mécanisme de
  remplacement.

## SEC-003 — Confirmation critique

- Date : 2026-09-28
- Décision technique : une action de niveau 3 exige un identifiant imprévisible,
  créé seulement après confirmation humaine, valable cinq minutes et
  consommable une seule fois. Il est lié à l'identité, l'action et la cible,
  puis supprimé au redémarrage du service de contrôle.
- Conséquence : un booléen `confirmed=true` produit par le modèle ne constitue
  plus une autorisation.

## ARC-CORE-001 — Registre et identité applicative

- Date : 2026-09-30
- Décision technique : les agents du lot 01 utilisent un contrat Pydantic
  immuable et un registre JSON atomique sous `$HERMES_HOME/arcenal`. Cette
  abstraction permet une migration SQLite ultérieure sans modifier ARC Core.
- Décision de sécurité : chaque application présente un secret dédié d'au
  moins 43 caractères ; l'identité utilisateur reste une dimension séparée.
- Conséquence : aucun repli vers ARC, aucune permission et aucune instruction
  système ne peuvent être demandés par le payload applicatif.

## RAG-001 — Index dérivé et ACL avant récupération

- Date : 2026-09-30
- Décision technique : les Markdown restent canoniques ; l'index JSON central
  est atomique, reconstructible et ne contient que leur projection normalisée.
- Décision de sécurité : le `ContextPlan` est construit côté serveur et les
  ACL filtrent les documents avant score, reranking et injection au modèle.
- Conséquence : l'ajout futur d'embeddings devra compléter le score derrière
  ce contrat sans contourner les ACL ni remplacer les sources originales.

## RAG-002 — SilverBullet comme coffre documentaire

- Date : 2026-09-30
- Décision utilisateur : écarter Nextcloud du périmètre RAG et retenir
  SilverBullet comme interface de rédaction et coffre de connaissances.
- Décision technique proposée : ARC reste l'unique moteur RAG, l'autorité ACL
  et le gestionnaire du workflow LDA. SilverBullet fournit les Markdown, les
  liens, les métadonnées et les révisions au travers de son API de fichiers.
- Conséquence : aucun second index RAG autonome n'est introduit. Le connecteur
  SilverBullet devra synchroniser par identifiants stables et `ETag`, puis
  alimenter l'index central dérivé sans exposer son jeton à l'interface.
- Sécurité : l'écriture SilverBullet sera réservée aux responsables autorisés ;
  le wiki salarié en lecture restera publié par ARC à partir des seules
  versions `Applicable`.
- Limite de présentation décidée par l'utilisateur : SilverBullet conserve son
  interface et son identité visuelle d'origine. Aucun thème ARCenal, fork
  graphique ou rebranding SilverBullet n'appartient au lot 03.

## RAG-003 — Mémoire d'entreprise comme collection gouvernée

- Date : 2026-09-30
- Décision : la mémoire d'entreprise est interrogeable par le RAG central mais
  reste une source distincte des documents applicables.
- Raison : un souvenir doit pouvoir être corrigé, expirer ou être oublié,
  tandis qu'un document conserve une version, une preuve et un workflow LDA.
- Conséquence : le Context Builder peut fusionner les passages documentaires et
  mémoriels après contrôle des ACL, sans transformer une mémoire en référence
  documentaire officielle ni en entrée automatique de la LDA.

## SEC-BKP-001 — Sauvegarde des secrets fournisseurs

- Date : 2026-10-01
- Décision : les secrets présents dans `/var/www/arcenal/data/.env` sont inclus
  dans la sauvegarde applicative YunoHost afin qu'une restauration retrouve un
  service autonome.
- Sécurité : le fichier reste en `0600`, le répertoire de données en `0700` et
  l'archive de sauvegarde doit être traitée comme un secret. Aucune valeur ne
  figure dans les snapshots ou documents versionnés.
- Conséquence : la recette de restauration vérifie le fonctionnement du secret
  par un appel, sans jamais afficher sa valeur. Une rotation reste obligatoire
  si la confidentialité de l'archive est douteuse.

## YNH-BOUNDARY-001 — YunoHost standard comme plateforme

- Date : 2026-10-01
- Décision utilisateur : ARCenal Système compose des applications sur un
  YunoHost standard ; il ne maintient ni fork obligatoire, ni patch du cœur, ni
  image système propre.
- Décision technique : les interactions passent par le packaging v2, les
  helpers, SSOwat et un broker allowlisté. L’adhésion globale de `www-data` à un
  groupe ARCenal a été supprimée au profit d’un socket directement groupé pour
  Nginx.
- Conséquence : toute nouvelle interaction YunoHost doit être classée et
  documentée dans `YUNOHOST_INTEGRATION_BOUNDARIES.md`.

## ARC-CONFIG-001 — Configuration native et adaptateur HERMES unique

- Date : 2026-10-01
- Décision : ARC dépend de `ArcConfigStore` et `ArcVault`. Le JSON natif et le
  fichier `.env` sont des backends remplaçables, non des contrats métier.
- Migration : l’adaptateur HERMES est en lecture seule ; une valeur native
  existante gagne et tout conflit est signalé sans écrasement.
- Sécurité : les secrets injectés au runtime ont priorité, les fichiers sont en
  `0600`, leurs répertoires en `0700` et aucune API ne renvoie leur contenu.
- Conséquence : tout nouvel import direct de `hermes_cli.config` hors de
  `hermes_config_adapter.py` est interdit et testé comme une régression.

## ARC-CONFIG-002 — ARC natif nominal et HERMES explicitement legacy

- Date : 2026-10-01
- Décision : l’absence de `ARCENAL_CONFIG_BACKEND` sélectionne ARC natif.
  `hermes` reste uniquement un mode explicite, diagnostiqué et en lecture seule.
- Migration : une ancienne configuration est copiée, vérifiée puis marquée une
  seule fois. ARC gagne les conflits, qui sont journalisés sans valeur sensible.
- Interface : les paramètres ARC utilisent `/configuration/v1` et les secrets
  les routes du coffre ; les parcours documentaires restent séparés.
- Conséquence : le prochain découplage concerne le runtime conversationnel,
  sans réimplémenter le RAG, la mémoire, le routage ou le cache.

## LOT10-PREVIEW-001 — Confidentialité et verdict priment sur le fallback

- Date : 2026-10-03
- Décision : ne pas abaisser automatiquement la classe de confidentialité
  `admin` d'ARC pour obtenir artificiellement un fallback OpenRouter.
- Raison : un repli n'est valide que si le modèle secondaire respecte le même
  contrat de données, de fournisseur et de harnais que le modèle primaire.
- Conséquence : la candidate ynh54 reste en Preview avec le verdict
  `HARDENING REQUIRED` jusqu'à l'attribution explicite d'un second modèle
  admissible et une preuve réelle de bout en bout.
