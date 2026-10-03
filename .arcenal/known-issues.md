# Points ouverts

## LOT10-ACCEPTANCE-001 — Preuves d'industrialisation incomplètes

- État : ouvert, verdict `HARDENING REQUIRED`.
- Impact : le défaut HIGH de repli sur erreur d'authentification ou de
  configuration est corrigé localement, mais la correction n'est ni publiée
  en preview ni recettée sur YunoHost.
- Preuves encore manquantes : parcours navigateur, changement réel de modèle,
  tâches et automatisations, versioning documentaire, SilverBullet, mémoire
  de recette, autorisation/refus broker et cycle destructif sur instance
  jetable.
- Prochaine étape : publier une seule candidate preview de hardening, la
  recetter sans nouveau développement fonctionnel, puis lever chaque réserve
  dans `docs/validation/LOT10_PREVIEW_ACCEPTANCE.md`.

## CHAT-MODEL-001 — Recette réelle du modèle Gemini

- État : la candidate `arcenal24` / `0.21.0~ynh42` restaure le catalogue des
  modèles, les politiques AUTO/FIXED et le traitement propre du quota. Sa
  publication preview et sa recette installée restent à effectuer.
- Cause confirmée : le serveur utilisait `provider: gemini` avec
  `default: auto`, valeur qui n’est pas un identifiant de modèle Gemini.
- Correctif : Paramètres synchronise désormais le modèle natif avec le moteur
  conversationnel ; l’interface, l’API et le panneau YunoHost refusent le
  pseudo-modèle `auto`. Le test Gemini n’envoie plus la clé comme un jeton
  OAuth Bearer et conserve uniquement le paramètre d’API attendu par Google.
  La mise à niveau remplace l'ancienne combinaison Gemini / `auto` par l'alias
  officiel `gemini-flash-latest` avant la migration vers le backend ARC.
- Preuves locales : Ruff, ESLint sans erreur, TypeScript, build, 16 tests API,
  37 tests web ciblés et 20 tests paquet réussissent. Les contrôles du
  catalogue GitHub et sa publication passent.
- Prochaine étape : installer ynh42 depuis le canal preview, vérifier le
  catalogue, AUTO/FIXED, le 429 propre et le contraste du chat, puis reprendre
  la recette Lot 09R. Ne pas promouvoir stable avant ces preuves.
- Dernière observation : le service serveur est actif et a redémarré à 16:38
  UTC, mais la version n'est pas lisible sans droits d'administration ; la
  confirmer dans YunoHost avant d'interpréter ce redémarrage comme une mise à
  niveau réussie.

## CDC-GAP-001 — Conformité fonctionnelle incomplète

- État : audit terminé, architecture validée et réalisation engagée.
- Impact : la version ynh34 sécurise l'installation et fournit les trois volets,
  mais plusieurs domaines du CDC détaillé sont absents ou partiels, notamment
  trois sections Paramètres, la gouvernance complète des agents, le système, la
  sécurité visible, les sauvegardes et le premier démarrage.
- Preuve : `docs/arcenal-product-audit.md` et
  `docs/arcenal-product-cdc-v2.md`.
- Prochaine étape : poursuivre les lots dans l'ordre défini par l'audit avec
  critères `AC-*` et recette installée.

## SEC-YH-001 — Recette YunoHost réelle requise

- État : recette non intrusive engagée sur le serveur principal ; la redirection
  SSO anonyme est prouvée. Les essais destructifs restent bloqués par l'absence
  d'une instance jetable.
- Impact : le découpage en trois services et les permissions des sockets ont
  été vérifiés statiquement et unitairement, mais pas encore installés sur la
  machine YunoHost de recette.
- Préparation : `docs/validation/YUNOHOST_ACCEPTANCE.md` contient la matrice et
  toutes les cases réelles restent bloquées ou non exécutées.
- Prochaine étape : poursuivre uniquement les essais `SAFE`, encadrer les
  essais `RISKY` par sauvegarde et récupération, puis réserver réinstallation,
  purge, restauration écrasante et corruption à une instance jetable.

## YNH-UPGRADE-001 — Relance de la mise à niveau ynh34 requise

- État : correctif publié, recette réelle en attente.
- Symptôme initial : la mise à niveau ynh33 s'arrêtait après la sauvegarde avec
  `Rien n'a été restauré` ; la sauvegarde cœur ne contenait aucun fichier et le
  démarrage du service de contrôle pouvait échouer avant la création du socket.
- Correctif : ynh34 crée le socket avec le groupe Nginx dès le démarrage et
  ajoute les unités systemd ainsi que la configuration Nginx à la sauvegarde
  cœur restaurable.
- Prochaine étape : actualiser le catalogue stable sur le serveur en ligne,
  relancer la mise à niveau et collecter le journal complet si elle échoue.

## TEST-001 — Suite Python historique indisponible localement

- État : résolu pour le périmètre ARCenal le 2026-09-30.
- Preuve : `.venv` Python 3.11.15 contient l'extra `dev` déclaré ; le lanceur
  canonique exécute 118 tests ARCenal avec succès, dont les 108 du lot 0.
- Limite amont : la suite exhaustive de 37 349 tests inclut des domaines
  optionnels dont les extras `acp` et `anthropic` ne font pas partie de `dev`.
  Son lancement a été interrompu à 3,2 % après confirmation de ces absences.
- Prochaine étape : laisser la CI amont exécuter la matrice de tous les extras,
  sans alourdir l'environnement local ARCenal avec des backends inutilisés.

## UI-THEME-001 — Recette visuelle installée à compléter

- État : correctif implémenté et validé statiquement.
- Impact : le contrat de thème, le chat et la couleur dominante sont couverts
  par TypeScript, Vitest et le build de production, mais les parcours complets
  clair, sombre et système n'ont pas été rejoués sur une installation YunoHost
  dans ce lot.
- Prochaine étape : vérifier sur la recette les messages ARC et utilisateur,
  Markdown, code, citations, défilement, formulaires, modales et notifications.

## UI-MARKDOWN-001 — Rendu Markdown volontairement léger

- État : ouvert, non bloquant.
- Impact : le chat réutilise désormais le rendu sécurisé commun, mais celui-ci
  ne couvre pas encore toute la spécification CommonMark.
- Prochaine étape : compléter le composant partagé uniquement si les usages
  métier du lot suivant nécessitent des constructions Markdown supplémentaires.

## UI-SETTINGS-001 — Onglets métier restants

- État : ouvert.
- Impact : Général, Apparence, Contexte, Directives, Mémoire et Outils disposent
  maintenant de parcours réels. Système et Sauvegardes restent à développer
  sans écran factice ; le centre de sécurité doit encore être approfondi.

## RAG-EXTRACTION-001 — Pièces jointes non extraites

- État : résolu au lot 03.
- Résolution : TXT, Markdown, DOCX et ODT sont extraits sans dépendance Python
  supplémentaire. Les PDF utilisent `pdftotext` lorsqu'il est disponible.
- Limite résiduelle : sans `pdftotext`, le PDF reste conservé et la fiche
  indique explicitement que son contenu n'a pas été extrait.

## RAG-SILVERBULLET-001 — Écriture distante différée

- État : limitation acceptée du lot 03.
- Impact : les pages SilverBullet sont synchronisées et indexées en lecture
  seule dans ARC. Leur modification s'effectue dans SilverBullet.
- Suite : une écriture distante conditionnelle par `If-Match` pourra être
  ajoutée après validation du modèle d'autorisations des responsables LDA.

## ARC-CONFIG-TRANSITION-001 — Adaptateur de migration HERMES

- État : chemin nominal résolu au Lot 09 ; compatibilité temporaire conservée.
- Impact : `HermesConfigAdapter` reste requis uniquement pour migrer une
  installation antérieure ou diagnostiquer un mode legacy explicite.
- Protection : aucun fallback silencieux ; l’adaptateur est en lecture seule et
  ne remplace jamais une valeur ARC divergente.
- Suite : le supprimer après preuve que le parc actif possède un marqueur de
  migration natif et n’utilise plus le mode legacy.

## ARC-RUNTIME-BOUNDARY-001 — Gateway conversationnel HERMES restant

- État : ouvert et cartographié au Lot 09.
- Impact : `_run_agent`, le streaming, les sessions et certains profils restent
  fournis par le runtime/dashboard HERMES.
- Protection : ARC contrôle déjà contexte, ACL, outils, RAG, mémoire, cache,
  routing et fournisseurs derrière ses contrats.
- Suite : Lot 10 proposé, limité à `ArcAgentRuntime` et à un adaptateur HERMES.

## LOT09R-DEPLOY-001 — Lot 09 absent du serveur principal

- État : fermé le 2026-10-03.
- Résolution : le serveur exécute le paquet preview `0.21.0~ynh53`, version
  applicative `0.21.0-arcenal35`, révision source
  `ff93c4c59f4307274163a264a94e44473b0ca2d0`.
- Preuves : backend `arc`, migration complète, coffre prêt, UMask `0077`,
  restart contrôlé, persistance, permissions, absence de secret dans les logs,
  parcours ARC corrélé et exécution ATS cloisonnée validés sur le serveur.
- Rapport : `docs/validation/LOT09R_PRODUCTION_COMPATIBILITY.md`.

## LOT10.1-FALLBACK-001 — Précondition du fallback réel non satisfaite

- État : preuve manquante, MEDIUM.
- Impact : AUTO sélectionne Gemini mais ne peut pas se replier vers les modèles
  OpenRouter découverts, dont la confidentialité reste `internal`.
- Protection : le routeur refuse le déclassement silencieux des données.
- Suite : utiliser le contrôle existant pour qualifier explicitement et auditer
  un modèle secondaire en `admin`, puis rejouer un 429/503/timeout contrôlé.

## LOT10.1-AUTOMATION-001 — Tâches hors circuit d'approbation

- État : fermé, anciennement HIGH.
- Correction : l'écran crée un workflow brouillon ; les transitions gouvernées
  pilotent le job cron associé.
- Preuve : cycle réel draft → testing → active, exécution réussie sur ynh56,
  sortie attendue, puis désactivation et suspension du job.

## LOT10.1-LDA-001 — V2 refusée sur le chemin de la V1

- État : fermé, anciennement HIGH.
- Correction : les révisions partagent une référence stable et reçoivent des
  chemins et répertoires de pièces jointes versionnés.
- Preuve : V1 et V2 chargées sans collision ; V2 approuvée, Applicable et seule
  version publiée dans le wiki.

## LOT10.1-BROKER-001 — Lectures envoyées sur le socket privilégié

- État : fermé, anciennement HIGH.
- Correction : l'API route `READ` vers `execute_readonly` ; le paquet autorise
  le journal CLI YunoHost requis sans élargir le catalogue d'actions.
- Preuve : `yunohost.version.read` répond `ok=true`, `code=0` sur ynh56 ; les
  actions hors catalogue restent refusées.

## LOT10.1-CHAT-001 — Erreur fournisseur trop technique

- État : ouvert, MEDIUM.
- Impact : le chat se débloque après un 429, mais affiche encore une charge
  Gemini brute, trop détaillée et peu exploitable pour un administrateur.
- Suite : conserver le diagnostic expurgé dans les logs et afficher dans le
  chat une erreur courte, française et actionnable.

## LOT10.1-YUNOHOST-001 — Détection plateforme incohérente

- État : ouvert, MEDIUM.
- Impact : Général affiche « YunoHost non détecté » sur l'instance YunoHost
  12.1.40.1 pourtant correctement reconnue par le paquet et les services.
- Suite : tracer la source de l'indicateur UI et la comparer à la détection
  serveur sans ajouter de privilège ni de lecture globale.

## LOT10.1-AUTOMATION-002 — Activation non atomique

- État : ouvert, MEDIUM.
- Impact : une erreur de persistance ou d'audit après la création du cron peut
  laisser un job technique sans liaison durable avec son workflow.
- Protection : la recette nominale et la recréation d'un cron manquant passent ;
  le cron piloté est masqué de l'interface générale.
- Suite : ajouter une compensation bornée ou une persistance transactionnelle
  sans nouvelle base ni nouveau service.

## LOT10.1-LDA-002 — Unicité référence/version non globale

- État : ouvert, MEDIUM.
- Impact : deux titres distincts pourraient enregistrer la même référence et la
  même version si leurs chemins canoniques diffèrent.
- Protection : le cycle demandé V1→V2 d'un même document refuse les doublons et
  conserve des chemins et pièces jointes distincts.
- Suite : contrôler globalement la paire `référence + version` avant écriture.
