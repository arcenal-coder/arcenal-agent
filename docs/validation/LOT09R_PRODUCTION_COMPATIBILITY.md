# Lot 09R — Compatibilité de production YunoHost

Date de recette : 2026-10-01
Branche locale : `arcenal`
Environnement visé : YunoHost principal `onyx-ingenierie.com`

## Verdict courant

```text
LOT 09 HARDENING REQUIRED
```

Ce verdict ne signale pas une régression locale. L'accès SSH sur le port 2403
a permis de prouver que la version installée est antérieure au Lot 09. La
recette de cette bascule ne peut donc pas être exécutée honnêtement sur ce code.
Aucun redémarrage, changement de secret ou paramètre de production n'a été
effectué sur cette version insuffisante.

## Contexte et règles appliquées

- Le serveur principal a été utilisé pour les contrôles HTTP publics autorisés.
- Aucune installation, restauration, désinstallation ou modification globale
  de YunoHost, Nginx ou SSOwat n'a été effectuée.
- Aucun secret, cookie, jeton ou mot de passe n'est conservé dans ce document.
- Les changements des Lots 01 à 09 restent locaux et non publiés. L'inventaire
  système confirme que leur présence sur le serveur ne peut pas être affirmée.

## État initial observable

| Mesure | Résultat réel | État | Preuve |
|---|---|---|---|
| HTTPS public | disponible | PASS | `https://onyx-ingenierie.com` répond via Nginx |
| Protection `/arcenal/` | redirection SSOwat | PASS | HTTP 302 vers `/yunohost/sso` |
| Faux `Remote-User` | aucune élévation | PASS | même HTTP 302 avec `Remote-User: forged-admin` |
| Charge HTTP légère | 10 réponses cohérentes | PASS | 10 HTTP 302, 66,5 à 79,8 ms |
| Session d'administration | application visible dans YunoHost | PASS partiel | titre de page Firefox authentifiée |
| SSH | disponible | PASS | port 2403, compte `guillaume.hausknecht`, clé dédiée |
| Version YunoHost | 12.1.40.1 | PASS | `dpkg-query`, sans élévation |
| Noyau | Debian 6.1.187-1 | PASS | `uname -a` |
| Version ARCenal installée | antérieure au Lot 09 | FAIL | bundle sans `/configuration/v1`, services démarrés le 28 septembre |
| Révision exacte installée | non lisible sans élévation | NON PROUVÉ | sources privées ; bundle `index-Bg7VDNUX.js` sans chaîne de version |
| Service ARCenal | actif, aucun restart systemd | PASS état | PID 1371300, `NRestarts=0` |
| Service de contrôle | actif | PASS état | PID 1371197 |
| Broker privilégié | actif | PASS état | PID 1371094 |
| Backend de configuration | ARC natif absent du bundle installé | FAIL | marqueurs Lot 09 absents des dix bundles JS déployés |
| État du coffre | coffre Lot 09 non prouvé sur la version installée | FAIL | diagnostic natif indisponible |
| UMask principal / broker | `0022` / `0022` | FAIL | propriétés systemd réelles ; attendu `0077` |
| UMask contrôle | `0007` | FAIL | attendu `0077` pour le Lot 09 |
| RAM systemd | 494 784 512 / 44 597 248 / 22 917 120 octets | PASS mesure | ARC / contrôle / broker avant restart |
| Première réponse locale | 4,5 ms, HTTP 200 | PASS mesure | `127.0.0.1:9121/` |

## Matrice de recette

| ID | Test | Résultat attendu | Résultat réel | État | Preuve |
|---|---|---|---|---|---|
| R09R-001 | ARC Native par défaut | backend `arc` | fonctionnalité Lot 09 absente du bundle installé | FAIL serveur | `/configuration/v1` absente |
| R09R-002 | Hermes Config absent du démarrage nominal | aucun chargement | non démontrable sur la version antérieure | FAIL serveur | diagnostic natif absent |
| R09R-003 | Paramètres généraux | lecture, écriture, persistance | API locale validée, écran serveur non manipulé | NON TESTÉ serveur | tests API Configuration |
| R09R-004 | Apparence | sauvegarde et restitution | API locale validée | NON TESTÉ serveur | tests de configuration et branding |
| R09R-005 | Onboarding | sauvegarde et restitution | API locale validée | NON TESTÉ serveur | tests API Configuration |
| R09R-006 | Accès | sauvegarde sans fuite | API locale validée | NON TESTÉ serveur | tests Vault et API |
| R09R-007 | Providers | configurations relues | neuf familles validées localement | NON TESTÉ serveur | tests fournisseurs multi-provider |
| R09R-008 | Modèles | modèle principal persistant | comportement local validé | NON TESTÉ serveur | tests API et invalidation ciblée |
| R09R-009 | Vault | prêt, secret non exposé | comportement local validé | NON TESTÉ serveur | tests Vault nominal/limites/rejet |
| R09R-010 | Rotation secret test | create/rotate/delete | comportement local validé | NON TESTÉ serveur | tests de rotation du paquet et API |
| R09R-011 | OpenRouter réel | appel court mesuré | credential et diagnostic serveur inaccessibles | NON TESTÉ | aucun secret réel manipulé |
| R09R-012 | `local_only` | zéro appel distant | validé localement | PASS local | tests ARC Frugal |
| R09R-013 | Agent ARC | réponse avec Config/RAG/mémoire | version Lot 09 non déployée | NON TESTÉ — version serveur insuffisante | arrêt de recette imposé |
| R09R-014 | Agent ATS et ACL | scopes bornés | version Lot 09 non déployée | NON TESTÉ — version serveur insuffisante | arrêt de recette imposé |
| R09R-015 | RAG LDA Applicable | bonne version, citation, ACL | validé localement | PASS local | tests RAG et LDA |
| R09R-016 | Enterprise Memory | créer, lire, corriger | validé localement | PASS local | tests mémoire d'entreprise |
| R09R-017 | Route déterministe | zéro appel LLM | validé localement | PASS local | tests ARC Frugal |
| R09R-018 | Cache | second appel sans LLM | validé localement | PASS local | tests ARC Frugal |
| R09R-019 | Workflow | exécution et exception contrôlée | validé localement | PASS local | tests du moteur d'automatisation |
| R09R-020 | Route LLM | fournisseur routé | adaptateurs validés sans appel payant | PASS local | tests Provider Architecture |
| R09R-021 | Changement de modèle | cache dépendant invalidé | validé localement | PASS local | tests Configuration API |
| R09R-022 | Pas d'invalidation globale | RAG/mémoire préservés | validé par contrat local | PASS local | invalidation limitée à `hermes-current` |
| R09R-023 | Restart ARC | service actif après redémarrage | volontairement non exécuté sur la version antérieure | NON TESTÉ — version serveur insuffisante | arrêt avant mutation |
| R09R-024 | Persistance après restart | valeurs et secrets conservés | non exécutable sans Lot 09 déployé | NON TESTÉ — version serveur insuffisante | dépend de R09R-023 |
| R09R-025 | Permissions | 0700/0600 et UMask 0077 | UMask principal, contrôle et broker non conformes | FAIL serveur | `0022`, `0007`, `0022` |
| R09R-026 | Logs sans secret | aucune donnée sensible | journaux nécessitant sudo non accessibles | NON TESTÉ | sudo exige un mot de passe |
| R09R-027 | Migration legacy | conversion complète | validé localement | PASS local | tests de migration et commande dédiée |
| R09R-028 | Migration idempotente | trois passages identiques | validé localement | PASS local | test en trois exécutions |
| R09R-029 | Conflit ARC/Hermes | ARC gagne sans fuite | validé localement | PASS local | test de conflit et journalisation |
| R09R-030 | Aucun fallback silencieux | erreur ARC propagée | validé localement | PASS local | test de configuration corrompue |
| R09R-031 | Mode legacy | explicite et lecture seule | validé localement | PASS local | test `ARCENAL_CONFIG_BACKEND=hermes` |
| R09R-032 | Health | arc/ready/complete | schéma local validé | NON TESTÉ serveur | API de santé locale |
| R09R-033 | SSO | utilisateur requis | redirection SSOwat observée | PASS | HTTP 302 |
| R09R-034 | Anti-usurpation | faux header refusé | redirection SSOwat inchangée | PASS | HTTP 302 avec faux `Remote-User` |
| R09R-035 | Core YunoHost inchangé | aucune mutation globale | aucune mutation exécutée par la recette | PASS recette | contrôles strictement en lecture |
| R09R-036 | Charge légère | 5 à 10 requêtes stables | 10 réponses cohérentes | PASS SSO | 66,5 à 79,8 ms, aucune erreur |

## Non-régression automatique

| Contrôle | Résultat |
|---|---:|
| Ruff ARC | PASS |
| ESLint | PASS, 0 erreur et 28 avertissements hérités |
| Syntaxe Bash | PASS |
| `ty` ciblé | PASS |
| TypeScript Web | PASS |
| TypeScript Dashboard | PASS |
| Compilation Python | PASS |
| Python ARC | 216 tests réussis |
| Frontend | 423 tests réussis, 64 fichiers |
| YunoHost shell | 9 scénarios réussis |
| Broker privilégié | 16 tests réussis |

Une première invocation de `ty` sur tout le dossier plugin ne configurait pas
la racine d'import du plugin et a produit des erreurs de résolution. La
commande ciblée avec `--extra-search-path plugins/arcenal-supervisor`, conforme
au périmètre Lot 09, réussit. Aucun code n'a été modifié pour contourner ce
problème de commande.

## Bugs trouvés

Aucun bug applicatif reproductible du Lot 09 n'a été trouvé pendant les tests
locaux. L'écart serveur est classé `BLOCKER` de recette : le Lot 09 n'est pas
réellement déployé. Les UMask observés confirment également que le paquet
installé précède le durcissement attendu.

## Contrôles restant obligatoires

1. Déployer de manière contrôlée une version contenant réellement le Lot 09.
2. Fournir `sudo` pour les lectures système et le restart encadré.
3. Relever backend, migration, coffre, disque et modes des fichiers sensibles.
4. Tester les écrans Paramètres et leur persistance réelle.
5. Tester un secret non critique dans le coffre du serveur.
6. Tester ARC, ATS, RAG, mémoire et ARC Frugal sur le runtime Lot 09.
7. Redémarrer le service puis vérifier persistance, permissions et journaux.
8. Contrôler l'absence de secrets et mesurer la RAM après redémarrage.

Tant que ces preuves manquent, les conditions de passage au Lot 10 ne sont pas
réunies et le commit final du Lot 09R ne doit pas être créé.

## Synthèse demandée

```yaml
Backend ARC serveur : FAIL
Hermes Config absent démarrage nominal : FAIL
Restart service : NON TESTÉ — version serveur insuffisante
Persistance : NON TESTÉ — version serveur insuffisante
Permissions : FAIL
Logs sans secret : NON TESTÉ — élévation requise
ARC réel : NON TESTÉ — version serveur insuffisante
ATS réel : NON TESTÉ — version serveur insuffisante
Version Lot 09 réellement déployée : NON
```

```text
LOT 09 HARDENING REQUIRED
```
