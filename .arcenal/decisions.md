# Décisions structurantes ARCenal Agent

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
