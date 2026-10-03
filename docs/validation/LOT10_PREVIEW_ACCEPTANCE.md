# ARCenal Agent — LOT 10.1 — Recette Preview

Date de recette : 2026-10-03

Périmètre : candidate Preview installée par la chaîne normale sur
`mail.onyx-ingenierie.com`. Aucun fichier applicatif n'a été copié manuellement
sur le serveur et aucun essai destructif n'a été réalisé sur l'instance
principale.

## Règles de preuve

Un résultat `PASS` exige une preuve produite sur la candidate publiée. Un test
local ne remplace pas une recette réelle. Les secrets ne sont ni affichés ni
recopiés dans ce rapport. Les valeurs antérieures du rapport LOT 10 restent
historiques et ne sont pas présentées comme des preuves LOT 10.1.

## Version publiée

```text
ARCenal : 0.21.0-arcenal38
Package YunoHost : 0.21.0~ynh58
Révision source : 3904adf3fbdaf723fb69bc91d0b6671e1d49286d
Révision package : bdc6a340d6b74eb30c96045135001df65075e920
Tag : v0.21.0-arcenal38
SHA-256 archive : 6ddf3f9024b231b9feb9addde13ca04929e5e7c589e97df4e8ce2fce01cc2452
Canal : preview
```

Le manifeste public Preview annonce bien `0.21.0~ynh58` et la révision package
attendue. Les workflows GitHub du catalogue `Verify` (37152957153) et `Publish`
(37152957170) sont réussis. Aucun changement ARCenal n'a été promu sur Stable.
Le dépôt applicatif ne déclenche pas de workflow sur la branche `arcenal` et le
dépôt du paquet n'expose pas de workflow : cette absence est une limite de
preuve CI, pas un succès implicite.

## Mise à jour YunoHost

La mise à jour a été effectuée avec le catalogue Preview et la commande normale
YunoHost. La sauvegarde de pré-mise à jour a été créée, puis le paquet ynh58 a
été installé avec succès.

```text
Version réellement installée : 0.21.0-arcenal38 / 0.21.0~ynh58
Révision réellement installée : 3904adf3fbdaf723fb69bc91d0b6671e1d49286d
Backend : arc
Migration : complete
Service principal : active/running
Services broker et contrôle : active/running
HTTP local : 200
Accès public anonyme : 302 vers le SSO YunoHost
UMask : 0077
Données : 0700 arcenal:arcenal
Configuration, coffre et bases sensibles contrôlés : 0600 arcenal:arcenal
```

Les empreintes de la configuration, du coffre, du registre des agents et des
bases ont été conservées pendant la mise à jour.

## Chat

```text
Gemini : PASS — réponse réelle exacte « RECETTE LOT 10.1 OK »
OpenRouter : FAIL — connexion réelle PASS, mais aucun modèle OpenRouter classé
             admin n'est attribuable à ARC ; aucun chat réel ARC/OpenRouter
Fallback : FAIL — en AUTO, le 429 Gemini n'a pas trouvé de candidat secondaire
429 : PARTIAL — l'attente se termine et le chat redevient utilisable, mais le
      message restitue encore une erreur fournisseur brute et trop détaillée
503 : NOT TESTED REAL — couvert uniquement en test local
Timeout : NOT TESTED REAL — couvert uniquement en test local
Persistance : PASS — conversation rouverte avec ses messages après navigation
Archivage : PASS — confirmation, archivage, puis nouvelle conversation
Thème : PARTIAL — contraste clair PASS et commutateurs clair/sombre/système PASS ;
        bulle du chat sombre non recapturée avant verrouillage du Mac
```

Le repli local est couvert pour `429`, `503` et délai dépassé, avec interdiction
sur authentification et configuration invalides. La preuve réelle demandée
`primary → erreur transitoire → secondary → réponse` n'a pas été obtenue : les
modèles OpenRouter découverts étaient encore classés `internal`. L'interface
permet déjà une qualification explicite et auditée en `admin` ; cette
précondition de recette n'a pas été satisfaite et ne doit pas être contournée
par un déclassement silencieux des données.

## Modèles

```text
Catalogue : PASS — 45 modèles Gemini et 100 modèles OpenRouter synchronisés
Filtre fournisseur : PASS
AUTO : PASS pour l'enregistrement et la persistance UI
FIXED : PASS pour l'enregistrement et la persistance UI
Changement modèle : PASS — FIXED → AUTO → FIXED sans erreur 500
Modèle réellement exécuté : PASS pour Gemini FIXED
Pseudo-modèle auto côté fournisseur : ABSENT
```

Le fournisseur ne porte aucun modèle par défaut : le choix reste dans le
harnais de chaque agent.

## Automatisations

```text
Tâches : PASS — la création produit un workflow brouillon gouverné
Workflow : PASS — draft → testing → active avec approbateur identifié
Exécution : PASS — job 1ee8e858c1b3 exécuté à 20:36:55 UTC
Résultat : PASS — sortie exacte « AUTOMATISATION GOUVERNÉE OK »
Suspension : PASS — workflow et deux recettes cron remis en veille
Registre UI : PASS — 2 cartes visibles, sans doublon technique du workflow
```

La contre-recette a créé le workflow
`recette-hardening-gouvernance-arc-musunpes` depuis l'interface. Son activation
a créé le job planifié, qui a utilisé le fournisseur configuré et produit son
fichier de sortie réel. La désactivation du workflow a suspendu le job associé.
Aucun état n'a été modifié directement pour simuler une réussite. Après
installation de ynh58 et rechargement sans cache, le registre affiche seulement
la tâche historique autonome et le workflow gouverné ; son cron technique
`1ee8e858c1b3` n'expose plus de commande directe de suppression ou d'activation.

## Documents

```text
Upload : PASS — fichier Markdown non sensible chargé et extrait
RAG : NOT TESTED REAL — quota Gemini épuisé et repli réel indisponible
Citation : NOT TESTED REAL
LDA : PASS — V1 et V2 portent la même référence métier sans collision
V1/V2 : PASS — chemins `procedure-recette-lot-10.md` et
        `procedure-recette-lot-10-v2.md`, pièces jointes séparées
Wiki : PASS — V2 approuvée, Applicable et seule version publiée dans le wiki
SilverBullet : NOT TESTED — connecteur non configuré, aucun état de
               synchronisation ni coffre SilverBullet présent sur le serveur
```

La contre-recette utilise la référence `PROCEDURE-RECETTE-LOT-10`. Le second
dépôt conserve cette référence, reçoit la version 2 et un chemin suffixé stable.
La V2 a suivi le circuit d'approbation avant sa publication dans le wiki.

## Supervision

```text
Diagnostic : PASS — santé du canal de contrôle et catalogue fermé de 16 actions
Autorisation : PASS — préparation de yunohost.version.read renvoie ready
Action : PASS — yunohost.version.read se termine avec `ok=true` et `code=0`
Routage : PASS — les niveaux READ utilisent le socket read-only
Audit : PASS — cycle d'action corrélé sans secret
Refus hors allowlist : PASS — shell.root.execute refusé en HTTP 422
```

Le refus hors allowlist reste inchangé. L'API de contrôle sélectionne maintenant
le client read-only pour une action `READ`. Le paquet autorise uniquement
l'écriture technique du journal CLI YunoHost dans `/var/log/yunohost`, nécessaire
à cette lecture, sans ouvrir d'autre chemin système au broker.

## Package

```text
Fresh install : NOT TESTED — INSTANCE JETABLE REQUIRED
Upgrade : PASS — mécanisme normal YunoHost/catalogue Preview
Backup : PASS — sauvegarde automatique de pré-mise à jour créée
Restore : NOT TESTED — INSTANCE JETABLE REQUIRED
Uninstall : NOT TESTED — INSTANCE JETABLE REQUIRED
Reinstall : NOT TESTED — INSTANCE JETABLE REQUIRED
```

## Ressources

```text
RAM service principal : 236 634 112 octets via systemd ; RSS 242 376 Kio
CPU idle observé : 1,3 % sur deux relevés espacés de 5 secondes
Chat Gemini réel : environ 30 secondes dans la recette navigateur
RAG : NOT MEASURED — requête réelle non aboutie
10 lectures HTTP séquentielles : 10/10 HTTP 200 ; 3,620 à 4,349 ms
10 lectures HTTP simultanées : 10/10 HTTP 200 ; 20,832 à 27,432 ms
SQLite locked : 0
Crash : 0
```

## Logs et secrets

Les journaux du service principal, du contrôle et du broker ont été inspectés
après la mise à jour et les essais. Sur la fenêtre finale de trois heures :

```text
Lignes du journal principal : 14
Marqueurs traceback/SQLite locked : 0
Marqueurs de secret : 0
```

Les messages d'erreur affichés dans le chat ne contenaient pas de secret, mais
leur charge fournisseur brute reste une régression d'expérience utilisateur.

## Tests

```text
Ruff : PASS
ESLint : PASS — 0 erreur, 28 avertissements historiques
ty : PASS
TypeScript web : PASS
TypeScript dashboard : PASS
Python ARCenal : 248 PASS
Frontend : 464 PASS
Build production : PASS
Paquet YunoHost : 20 tests Python PASS et 9 scripts PASS
Catalogue : 13 PASS
Hardening ciblé : 13 tests Python et 7 tests frontend PASS
Reproductibilité des canaux : PASS
git diff --check : PASS avant publication
```

## Bugs

### LOT10.1-BUG-002 — Gouvernance des tâches non reliée à l'écran planifié

- sévérité : HIGH ;
- cause : l'écran crée directement un job cron actif au lieu d'un
  `AutomationCandidate` brouillon soumis à approbation ; le scheduler n'exécute
  pas le job créé ;
- correction : l'écran crée un workflow gouverné ; l'activation approuvée crée
  ou reprend son job cron et la désactivation le suspend ;
- preuve : cycle navigateur draft → testing → active, exécution réelle à
  20:36:55 UTC et sortie attendue ; le cron technique piloté est masqué de
  l'interface et recréé s'il manque lors d'une activation ;
- état : FERMÉ.

### LOT10.1-BUG-003 — Collision du versionnement LDA

- sévérité : HIGH ;
- cause : l'upload transforme le titre en chemin unique et refuse un document
  déjà présent avant de créer une nouvelle version ;
- correction : une nouvelle révision reçoit un chemin versionné et un répertoire
  de pièces jointes distinct ; une version déjà présente reste refusée ;
- preuve : V1 et V2 chargées sous la même référence, V2 Applicable et visible
  dans le wiki ;
- état : FERMÉ.

### LOT10.1-BUG-004 — Action de lecture envoyée au mauvais socket

- sévérité : HIGH ;
- cause : `control_api.py` utilise le client du socket privilégié pour toutes
  les actions, au lieu d'utiliser `execute_readonly` pour les actions READ ;
- correction : le niveau `READ` sélectionne `execute_readonly` et l'unité broker
  autorise le seul journal CLI requis par YunoHost ;
- preuve : préparation `ready`, exécution terminée avec `ok=true`, `code=0` et
  version YunoHost retournée ;
- état : FERMÉ.

### LOT10.1-BUG-005 — Erreur fournisseur trop technique

- sévérité : MEDIUM ;
- cause : le rendu du chat conserve la charge textuelle détaillée de Gemini ;
- correction : aucune dans ce lot ;
- preuve : erreur 429 réelle affichée, chat débloqué ;
- état : OUVERT.

### LOT10.1-BUG-006 — Détection YunoHost incohérente dans Général

- sévérité : MEDIUM ;
- cause : à diagnostiquer ; l'écran indique « YunoHost non détecté » alors que
  l'application s'exécute sur YunoHost 12.1.40.1 ;
- correction : aucune dans ce lot ;
- preuve : recette navigateur et contrôle serveur ;
- état : OUVERT.

### LOT10.1-BUG-007 — Atomicité création cron / persistance workflow

- sévérité : MEDIUM ;
- cause : lors d'une activation, le cron est créé avant la persistance du
  workflow et de son audit, sans compensation si cette seconde étape échoue ;
- correction : aucune dans ce lot, le scénario nominal est validé ;
- preuve : revue indépendante du chemin d'activation après `3904adf3fb` ;
- état : OUVERT.

### LOT10.1-BUG-008 — Unicité globale référence/version LDA

- sévérité : MEDIUM ;
- cause : l'unicité `référence + version` est contrôlée lors du versionnement
  d'un chemin existant, mais pas encore globalement pour deux titres distincts ;
- correction : aucune dans ce lot, le scénario V1→V2 demandé est validé ;
- preuve : revue indépendante de la création documentaire après `795e3f3233` ;
- état : OUVERT.

## Skills réellement utilisées

```text
arcenal-gauntlet — conduite du diagnostic, validation et mémoire projet
agent-harness — plan persistant T1–T9, tentatives bornées et preuves
skill-security-auditor — audit avant installation des skills externes
rag-architect — analyse ciblée du versionnement LDA
observability-designer — analyse ciblée du routage broker et de l'audit
pr-review-expert — revue finale indépendante du diff et des preuves
```

Les skills conditionnelles de dépendance, performance et incident n'ont pas été
activées : aucune dépendance n'a changé, aucun risque de performance nouveau et
aucun incident serveur n'ont été constatés.

## Verdict

```text
THREE HIGH DEFECTS CLOSED
```

Les trois défauts HIGH du hardening ciblé sont corrigés et prouvés sur la
candidate Preview réellement installée. Les limites antérieures hors périmètre
restent documentées : fallback réel non recetté, message fournisseur trop
technique, détection YunoHost incohérente, atomicité cron/workflow, unicité
globale référence/version LDA et SilverBullet non configuré.

Cette clôture n'autorise ni promotion Stable ni nouveau lot fonctionnel. Elle
ferme uniquement les trois HIGH explicitement confiés à ce hardening.

---

## LOT 10.3 — Integrity Closure

### Candidate recettée

```text
ARCenal Agent : 0.21.0-arcenal41
Paquet YunoHost : 0.21.0~ynh61
Révision source : 668ca31afdb4fcf7dd9a05c392eabc1e526b905b
Révision package : dbb99bba6e9e3b46d20d3e214c177ec25632f9d2
Catalogue Preview : 7cf7be8402816335a24bb95d1a77a421521d795f
Stable modifié : NON
```

### MEDIUM-01 — Atomicité des automatisations

La cause était l'ordre non compensé entre création/reprise du cron,
persistance du workflow et audit, aggravé par les activations concurrentes et
par l'héritage d'une limite d'une exécution sur les planifications récurrentes.
Le correctif sérialise la transition, n'expose l'état actif qu'après
confirmation, compense les échecs et remplace de manière gouvernée un ancien
cron récurrent terminal.

Les tests couvrent les échecs scheduler, persistance et audit, le rollback,
l'idempotence et la concurrence. Sur YunoHost, le workflow
`recette-lot-10-3-atomicite-musx37zx` a conservé un seul cron
`c27f9850f31d`. Une exécution réelle a fait passer son compteur de 0 à 1 le
3 octobre 2026 à 22:12:30 UTC, tout en gardant `enabled=true`,
`state=scheduled` et `repeat.times=null`. La suspension a produit
`enabled=false/state=paused`; la réactivation a repris le même identifiant et
le restart du seul service ARCenal a conservé workflow, cron et historique.
L'audit chaîné contient les transitions, y compris un échec contrôlé resté
hors de l'état actif.

```text
Activation nominale : PASS
Échec scheduler : PASS
Échec persistence : PASS
Rollback : PASS
Idempotence : PASS
Concurrence : PASS
Absence doublon : PASS
Suspension : PASS
Restart : PASS
Audit : PASS
MEDIUM-01 : CLOSED
```

### MEDIUM-02 — Intégrité LDA

La source canonique est le coffre Markdown, pas une table SQLite. Le contrôle
historique était court-circuité pour un nouveau chemin et ne protégeait pas
deux créations concurrentes. La paire est maintenant normalisée en Unicode
NFKC puis trim/casefold et contrôlée sous verrou processus et interprocessus
avant écriture atomique. Un doublon retourne un HTTP 409 métier.

La recette réelle a créé V1, V2 et V3 pour
`RECETTE-INTEGRITE-LOT-10-3`. Les secondes créations exactes de V2 et V3 ont
été refusées. V1 est archivée, V2 est Applicable et V3 reste À approuver ;
le RAG et le wiki ne présentent que V2 comme version officielle. L'index et
l'historique persistent après upgrade et restart.

```text
Audit données existantes : PASS
Contrainte source de vérité : PASS
Migration idempotente : PASS — aucun stockage à migrer
V1/V2/V3 : PASS
Doublon : REFUSED
Concurrence : PASS
API conflict : PASS — HTTP 409
Frontend conflict : PASS
Historique : PASS
Applicable/obsolete : PASS
RAG : PASS
Wiki : PASS
MEDIUM-02 : CLOSED
```

### Non-régression et exploitation

- Ruff, ty, TypeScript et build de production passent.
- 36 tests Python ciblés, 273 tests Python ARCenal et 464 tests frontend
  passent.
- Le paquet passe 20 tests Python et 9 scripts YunoHost ; le catalogue passe
  13 tests. Les deux CI Preview sont vertes.
- `arcenal`, `arcenal_control` et `arcenal_broker` sont actifs ; l'interface
  locale répond HTTP 200 après restart.
- Backend et coffre ARC sont actifs. Les données sensibles sont en `0600`, le
  répertoire en `0700` et l'unité applique `UMask=0077`.
- Les journaux post-upgrade et post-restart ne contiennent ni traceback,
  verrou de base inattendu, erreur de permission, ni valeur de credential.
- OpenRouter n'est pas retesté dans ce lot : aucun changement ne touche les
  fournisseurs.

### Revue et dette restante

La revue indépendante conclut à 0 BLOCKER, 0 HIGH et 0 MEDIUM. Un LOW reste
documenté : absence de test négatif dédié garantissant la conservation de
l'identifiant d'un cron récurrent en état `error` récupérable. Aucune
dépendance, base, unité ou architecture n'a été ajoutée.

Les cycles fresh install, restore, uninstall et reinstall ne sont pas testés
sur le serveur principal, conformément à l'interdiction des essais destructifs.
Ils exigent une instance YunoHost jetable.

### Verdict LOT 10.3

```text
STABLE CANDIDATE — INSTANCE JETABLE PACKAGE RECIPE REQUIRED
```

Prochaine étape unique : `RECETTE PACKAGE SUR INSTANCE YUNOHOST JETABLE`.
