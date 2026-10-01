# Points ouverts

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

- État : ouvert et bloquant pour le verdict de recette, observé le 2026-10-01.
- Symptôme : l'accès SSH sur le port 2403 fonctionne et les services ARCenal
  sont actifs, mais le bundle servi ne contient aucun marqueur de l'API native
  `/configuration/v1`. Les services ont été démarrés avant la création locale
  du Lot 09.
- Impact : backend ARC, absence de Hermes Config, restart, persistance, ARC et
  ATS ne peuvent pas être validés sur cette version. Les UMask réels `0022`,
  `0007`, `0022` sont également antérieurs au durcissement `0077` attendu.
- Contrôles indépendants : SSOwat, anti-usurpation, état systemd et suites
  locales passent. Les journaux et modes des fichiers sensibles nécessitent
  encore une élévation non interactive indisponible.
- Prochaine étape : déployer de manière contrôlée le Lot 09, puis reprendre les
  seules preuves système manquantes avec une voie d'élévation autorisée.
