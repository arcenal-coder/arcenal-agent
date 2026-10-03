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
ARCenal : 0.21.0-arcenal36
Package YunoHost : 0.21.0~ynh54
Révision source : 4b7acf426fda42fd8576dbc764dd2360b6f3502a
Révision package : d2a3c0c5f0fe1506123f0f6ccb253b27ca386a39
Tag : v0.21.0-arcenal36
SHA-256 archive : 6e533aa82f518a5e7fd20755fb761e7c34a63a857851897cad61a8269755bc74
Canal : preview
```

Le manifeste public Preview annonce bien `0.21.0~ynh54` et la révision package
attendue. Les workflows GitHub du catalogue `Verify` (37145603259) et `Publish`
(37145603380) sont réussis. Aucun changement ARCenal n'a été promu sur Stable.
Le dépôt applicatif ne déclenche pas de workflow sur la branche `arcenal` et le
dépôt du paquet n'expose pas de workflow : cette absence est une limite de
preuve CI, pas un succès implicite.

## Mise à jour YunoHost

La mise à jour a été effectuée avec le catalogue Preview et la commande normale
YunoHost. La sauvegarde de pré-mise à jour a été créée, puis le paquet ynh54 a
été installé avec succès.

```text
Version réellement installée : 0.21.0-arcenal36 / 0.21.0~ynh54
Révision réellement installée : 4b7acf426fda42fd8576dbc764dd2360b6f3502a
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
Tâches : FAIL — la tâche de recette est créée active malgré le libellé
         « Créer en brouillon » et n'est pas exécutée à l'échéance
Workflow : FAIL — aucun circuit draft → approval → active n'est relié aux
           tâches planifiées de l'interface
Historique : FAIL — aucun historique d'exécution exploitable dans l'écran
Suspension : PASS — la tâche 639f8a02d310 est finalement suspendue
```

La tâche non dangereuse demandait uniquement un bref état de disponibilité
d'ARC. Elle avait une cadence d'une minute ; `last_run_at` est resté nul après
l'échéance. Les marqueurs du ticker étaient anciens. Aucun état n'a été modifié
directement pour simuler une réussite.

## Documents

```text
Upload : PASS — fichier Markdown non sensible chargé et extrait
RAG : NOT TESTED REAL — quota Gemini épuisé et repli réel indisponible
Citation : NOT TESTED REAL
LDA : PARTIAL — document V1 stocké en 0600 et placé « À approuver »
V1/V2 : FAIL — le chargement de V2 renvoie HTTP 409 car le chemin dérivé du
        titre existe déjà ; V1 ne peut donc pas devenir obsolète au profit de V2
Wiki : FAIL — aucune V2 Applicable à publier
SilverBullet : NOT TESTED — connecteur non configuré, aucun état de
               synchronisation ni coffre SilverBullet présent sur le serveur
```

Le champ de numérotation `REC-LDA-LOT10` est bien conservé dans les métadonnées,
mais le chemin canonique est dérivé du titre (`procedure-recette-lot-10.md`). Le
second dépôt utilisant le même titre est refusé avant le circuit de version.

## Supervision

```text
Diagnostic : PASS — santé du canal de contrôle et catalogue fermé de 16 actions
Autorisation : PASS — préparation de yunohost.version.read renvoie ready
Action : FAIL — le broker refuse ensuite cette action allowlistée avec
         « Action privilégiée non autorisée »
Audit : PASS — action.requested puis action.failed, intégrité déclarée vraie
Refus hors allowlist : PASS — shell.root.execute refusé en HTTP 422
```

Le refus hors allowlist est correct. En revanche, l'API de contrôle envoie
toutes les exécutions vers le socket privilégié, y compris les actions de
lecture prévues pour le socket read-only. Le broker refuse donc correctement la
lecture sur le mauvais canal ; la chaîne complète de supervision n'est pas
validée.

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
Python ARCenal : 242 PASS
Frontend : 463 PASS
Build production : PASS
Paquet YunoHost : 20 tests Python PASS et 9 scripts PASS
Catalogue : 13 PASS
Reproductibilité des canaux : PASS
git diff --check : PASS avant publication
```

## Bugs

### LOT10.1-BUG-002 — Gouvernance des tâches non reliée à l'écran planifié

- sévérité : HIGH ;
- cause : l'écran crée directement un job cron actif au lieu d'un
  `AutomationCandidate` brouillon soumis à approbation ; le scheduler n'exécute
  pas le job créé ;
- correction : aucune dans ce lot ;
- preuve : libellé « Créer en brouillon », état actif immédiat, puis
  `last_run_at=null` après échéance ;
- état : OUVERT.

### LOT10.1-BUG-003 — Collision du versionnement LDA

- sévérité : HIGH ;
- cause : l'upload transforme le titre en chemin unique et refuse un document
  déjà présent avant de créer une nouvelle version ;
- correction : aucune dans ce lot ;
- preuve : V1 créée, V2 de même référence refusée en HTTP 409 ;
- état : OUVERT.

### LOT10.1-BUG-004 — Action de lecture envoyée au mauvais socket

- sévérité : HIGH ;
- cause : `control_api.py` utilise le client du socket privilégié pour toutes
  les actions, au lieu d'utiliser `execute_readonly` pour les actions READ ;
- correction : aucune dans ce lot ;
- preuve : préparation `ready`, exécution HTTP 500, audit `action.failed` ;
- état : OUVERT.

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

## Skills réellement utilisées

```text
arcenal-gauntlet — conduite du diagnostic, validation et mémoire projet
piloter-projet-digital — matrice de recette et contrôle du périmètre
```

`agent-harness` et les skills tierces suggérées n'étaient pas disponibles ;
elles n'ont été ni installées ni déclarées comme utilisées.

## Verdict

```text
HARDENING REQUIRED
```

Motifs déterminants : trois défauts HIGH ouverts, chat OpenRouter non prouvé,
fallback réel non recetté, automatisations non gouvernées et non exécutées,
versionnement documentaire bloqué, supervision allowlistée inexécutable et
SilverBullet non configuré.

Suite unique proposée : `hardening supplémentaire`, limité à la correction et
à la contre-recette de ces écarts. Aucun lot fonctionnel suivant ne doit être
commencé et aucune promotion Stable ne doit être effectuée.
