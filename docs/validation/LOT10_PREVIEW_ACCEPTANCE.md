# ARCenal Agent — LOT 10 — Recette Preview

Date de recette : 2026-10-03

État : TERMINÉ — réserves bloquantes documentées

Périmètre : version Preview installée sur `mail.onyx-ingenierie.com` et correction locale candidate non publiée.

## Règles de preuve

Un résultat `PASS` n'est attribué qu'avec une preuve locale, YunoHost réelle ou fournisseur réel. Les validations du LOT 09R servent de baseline sans être présentées comme de nouvelles preuves. Les essais destructifs de paquet restent interdits sur le serveur principal.

## Preuves détaillées

### LOT10-LLM-001 — Repli après indisponibilité temporaire

- fonction : résilience multi-fournisseur AUTO ;
- environnement : LOCAL TEST ;
- précondition : deux fournisseurs et deux modèles admissibles ;
- action : le premier fournisseur renvoie une indisponibilité HTTP 503 simulée ;
- résultat attendu : un seul repli borné vers le second candidat ;
- résultat réel : le second fournisseur répond ;
- preuve : `tests/arcenal_security/test_provider_architecture.py::test_auto_mode_falls_back_after_gemini_503` ;
- état : PASS ;
- bug éventuel : aucun.

### LOT10-LLM-002 — Repli après expiration de délai

- fonction : résilience multi-fournisseur AUTO ;
- environnement : LOCAL TEST ;
- précondition : deux fournisseurs et deux modèles admissibles ;
- action : le premier fournisseur lève une expiration de délai simulée ;
- résultat attendu : repli vers le second candidat ;
- résultat réel : le second fournisseur répond ;
- preuve : `tests/arcenal_security/test_provider_architecture.py::test_auto_mode_falls_back_after_provider_timeout` ;
- état : PASS ;
- bug éventuel : aucun.

### LOT10-LLM-003 — Absence de repli sur erreur non transitoire

- fonction : politique de sécurité du repli ;
- environnement : LOCAL TEST ;
- précondition : deux fournisseurs admissibles ;
- action : HTTP 401 puis HTTP 404 dans deux scénarios isolés ;
- résultat attendu : aucune nouvelle tentative et aucun appel au fournisseur suivant ;
- résultat réel : l'erreur `authentication` ou `configuration` est propagée après le seul appel initial ;
- preuve : `tests/arcenal_security/test_provider_architecture.py::test_auto_mode_never_falls_back_on_non_temporary_provider_errors` ;
- état : PASS ;
- bug éventuel : `LOT10-BUG-001`, corrigé localement.

### LOT10-LLM-004 — Politique local_only

- fonction : interdiction stricte des fournisseurs distants ;
- environnement : LOCAL TEST ;
- précondition : seul un modèle distant est enregistré ;
- action : routage d'une demande `local_only` ;
- résultat attendu : zéro appel distant ;
- résultat réel : aucun modèle distant n'est sélectionné ;
- preuve : `tests/arcenal_security/test_provider_architecture.py::test_local_only_never_calls_remote_provider` ;
- état : PASS ;
- bug éventuel : aucun.

### LOT10-LLM-005 — Appel Gemini réel

- fonction : fournisseur primaire ;
- environnement : REAL PROVIDER TEST ;
- précondition : secret Gemini présent dans le coffre serveur ;
- action : appel court à `gemini-3-flash-preview` ;
- résultat attendu : HTTP 200 et réponse finale exploitable ;
- résultat réel : HTTP 200, `LOT10-GEMINI-OK`, terminaison `STOP`, 1,341 s ;
- preuve : appel depuis le serveur, secret chargé sans affichage ;
- état : PASS ;
- bug éventuel : aucun.

### LOT10-LLM-006 — Appel OpenRouter réel

- fonction : second fournisseur distant ;
- environnement : REAL PROVIDER TEST ;
- précondition : secret OpenRouter présent dans le coffre serveur ;
- action : appel court à `cohere/north-mini-code:free` ;
- résultat attendu : HTTP 200 et contenu exploitable ;
- résultat réel : HTTP 200, un choix, `LOT10-OPENROUTER-OK`, coût déclaré nul ;
- preuve : appel depuis le serveur, secret chargé sans affichage ;
- état : PASS ;
- bug éventuel : aucun.

### LOT10-YNH-001 — Redémarrage et persistance

- fonction : redémarrage contrôlé du service ARCenal ;
- environnement : REAL YUNOHOST TEST ;
- précondition : `arcenal.service` actif ;
- action : empreinte des configurations, redémarrage du seul service, nouvelle empreinte ;
- résultat attendu : nouveau processus, retour HTTP, données inchangées ;
- résultat réel : PID `42011` remplacé par `85207`, HTTP 200 après démarrage, quatre empreintes identiques ;
- preuve : `config.json`, `agents.json`, `chat-sessions.json` et `.env` comparés avant/après ;
- état : PASS ;
- bug éventuel : le premier contrôle HTTP était trop précoce, puis le service a répondu normalement après 33 secondes.

### LOT10-YNH-002 — Permissions, services et journaux

- fonction : exploitation YunoHost non intrusive ;
- environnement : REAL YUNOHOST TEST ;
- précondition : paquet `0.21.0~ynh53` installé ;
- action : contrôle des unités, modes, propriétaire, UMask et journaux ;
- résultat attendu : services actifs, 0700/0600, UMask 0077, aucun secret ;
- résultat réel : six unités ARCenal contrôlées actives, propriétaire `arcenal:arcenal`, modes et UMask conformes, zéro motif de secret et zéro avertissement après redémarrage ;
- preuve : état systemd, métadonnées de fichiers et journal local ;
- état : PASS ;
- bug éventuel : aucun.

### LOT10-PERF-001 — Charge HTTP légère

- fonction : disponibilité et concurrence légère ;
- environnement : REAL YUNOHOST TEST ;
- précondition : service revenu actif après redémarrage ;
- action : dix lectures HTTP simultanées ;
- résultat attendu : dix HTTP 200, aucun blocage SQLite ;
- résultat réel : 10/10 HTTP 200, maximum 17,908 ms, zéro verrou SQLite journalisé ;
- preuve : mesures `curl` locales au serveur et contrôle du journal ;
- état : PASS ;
- bug éventuel : aucun.

### LOT10-UI-001 — Recette visuelle réelle

- fonction : Chat, Conversations, Agents, Tâches planifiées, RAG/LDA et Paramètres ;
- environnement : REAL YUNOHOST TEST ;
- précondition : session SSO administrateur inspectable ;
- action : parcours navigateur ;
- résultat attendu : parcours complet avec thèmes et contraste ;
- résultat réel : aucune session navigateur inspectable n'a permis de produire une preuve reproductible ;
- preuve : aucune preuve visuelle exploitable ;
- état : BLOCKED ;
- bug éventuel : aucun bug produit attribué sans constat.

### LOT10-PKG-001 — Cycle destructif du paquet

- fonction : fresh install, restauration et désinstallation ;
- environnement : NOT TESTED ;
- précondition : instance YunoHost jetable ;
- action : aucune sur le serveur principal ;
- résultat attendu : cycle complet ;
- résultat réel : instance jetable absente ;
- preuve : règle de non-destruction du serveur principal ;
- état : NOT TESTED ;
- bug éventuel : aucun.

## A — Version testée

```text
ARCenal : 0.21.0-arcenal35
YunoHost package : 0.21.0~ynh53
Révision serveur : ff93c4c59f4307274163a264a94e44473b0ca2d0
Révision locale de référence : 9c46f8fce4, avec correction LOT 10 non commitée
Canal : preview
```

## B — Chat

```text
Nouvelle conversation : NOT TESTED
Réponse : PASS en REAL PROVIDER TEST, parcours UI non testé
Persistance : PASS — 8 conversations conservées après restart
Réouverture : NOT TESTED — présence en stockage prouvée, interaction UI non prouvée
Archivage : PASS pour l'état stocké — 7 archivées ; action UI non testée
Erreur provider : PASS en LOCAL TEST ; rendu UI réel non testé
Contraste/thème : PASS en tests frontend ; recette visuelle réelle BLOCKED
```

## C — Agents

```text
Création : NOT TESTED
Modification : NOT TESTED
AUTO : PASS en tests ; ATS configuré AUTO sur serveur, exécution LOT 09R seulement
FIXED : PASS en tests ; ARC configuré FIXED sur serveur, exécution LOT 09R seulement
Changement modèle : NOT TESTED dans cette recette
ACL : PASS — baseline LOT 09R et tests de non-régression
```

## D — LLM

| Provider | Configuré | Contrat testé | Appel réel | Modèle | Résultat | Fallback |
|---|---:|---:|---:|---|---|---:|
| Gemini | oui | oui | oui | `gemini-3-flash-preview` | PASS | LOCAL TEST |
| OpenRouter | oui | oui | oui | `cohere/north-mini-code:free` | PASS | LOCAL TEST |
| OpenAI | non | oui | non | — | NOT CONFIGURED | non |
| Anthropic | non | oui | non | — | NOT CONFIGURED | non |
| Mistral | non | oui | non | — | NOT CONFIGURED | non |
| Ollama | oui | oui | non | aucun modèle observé | UNAVAILABLE | non |
| vLLM | non | oui | non | — | NOT CONFIGURED | non |

```text
Fallback 429 : PASS en LOCAL TEST
Fallback 503 : PASS en LOCAL TEST
Fallback timeout : PASS en LOCAL TEST
Absence de fallback 401/404 : PASS en LOCAL TEST
local_only : PASS en LOCAL TEST
Fallback réel de bout en bout : NOT TESTED — ne pas provoquer une panne externe
Registre serveur : 145 modèles, dont 45 Gemini et 100 OpenRouter
```

## E — Documents

```text
Upload : NOT TESTED
Indexation : PASS pour l'état existant — 1 document et 2 fragments
Recherche/RAG : PASS — baseline LOT 09R, stockage intact après restart
Citation : PASS — baseline LOT 09R, non rejouée dans cette recette
LDA : PASS — baseline LOT 09R, workflow de recette non rejoué
V1/V2 : NOT TESTED
Wiki : PASS — baseline LOT 09R, publication non rejouée
SilverBullet : NOT TESTED — connecteur non configuré sur le serveur
```

## F — Automatisations

```text
Tâche créée : NOT TESTED
Validation : NOT TESTED
Activation : NOT TESTED
Exécution : NOT TESTED
Historique : NOT TESTED
Suspension : NOT TESTED
Workflow : NOT TESTED
Exception : NOT TESTED
```

Aucun registre de workflow de recette n'était présent sur l'instance. Aucun état artificiel n'a été créé directement dans les données.

## G — Supervision

```text
Diagnostic : PASS — baseline LOT 09R
Rapport : PASS — baseline LOT 09R
Proposition : NOT TESTED dans cette recette
Autorisation : NOT TESTED dans cette recette
Exécution : NOT TESTED dans cette recette
Vérification : PASS pour l'état des services
Audit : PASS — 16 événements, dont requêtes, RAG et mémoire
Refus action interdite : NOT TESTED dans cette recette
```

## H — YunoHost

```text
Upgrade réel : PASS — package ynh53 déjà installé
Restart : PASS — service ARCenal uniquement
Persistance : PASS — quatre empreintes inchangées
Fresh install : NOT TESTED — INSTANCE JETABLE REQUIRED
Backup : PASS — baseline LOT 09R
Restore : NOT TESTED — INSTANCE JETABLE REQUIRED
Uninstall : NOT TESTED — INSTANCE JETABLE REQUIRED
```

## I — Ressources

```text
RAM après restart : 134,9 MiB
Tâches systemd avant restart : 10
RAM observée avant restart : 271,3 MiB
10 lectures HTTP simultanées : 10/10 HTTP 200
Temps maximal des 10 lectures : 17,908 ms
Blocage SQLite observé : 0
Gemini réel : 1,341 s
```

La variation mémoire avant/après ne constitue pas un benchmark de fuite : les durées d'activité diffèrent.

## J — Tests

```text
Ruff ciblé : PASS
ESLint : PASS — 0 erreur, 28 avertissements historiques
ty ciblé : PASS
TypeScript web : PASS
TypeScript dashboard : PASS
Python ARCenal : 242 tests PASS, 1 avertissement de dépendance
Frontend : 463 tests PASS dans 68 fichiers
Build production : PASS
Paquet YunoHost : 20 tests Python PASS et 9 scripts PASS
Catalogue : 13 tests PASS
ShellCheck : NOT TESTED — TOOL UNAVAILABLE
git diff --check : PASS
```

## K — Bugs

### LOT10-BUG-001

- sévérité : HIGH tant que la correction n'est pas publiée et recettée ;
- cause : les erreurs fournisseur étaient converties en indisponibilité temporaire ; un 429 Gemini textuel n'était pas reconnu et un 401 encapsulé pouvait être masqué par le message transitoire de son exception externe ;
- correction : classification explicite, priorité des statuts structurés non transitoires sur toute la chaîne d'erreurs, reconnaissance des 429 textuels et séparation des conditions de nouvelle tentative et de repli ;
- preuve : tests `LOT10-LLM-001` à `LOT10-LLM-004`, suite ARCenal et build ;
- état : CORRIGÉ LOCALEMENT, NON PUBLIÉ, NON RECETTÉ SUR YUNOHOST.

## L — Dette restante

- publier une future candidate Preview contenant `LOT10-BUG-001`, puis la recetter réellement ;
- terminer les parcours navigateur Chat, historique, thèmes, Agents, Modèles et Paramètres ;
- recetter tâches planifiées et automatisations avec données non dangereuses ;
- recetter upload, versioning LDA V1/V2 et SilverBullet configuré ;
- recetter Enterprise Memory avec une donnée de recette nettoyée ensuite ;
- recetter une autorisation broker et un refus hors allowlist ;
- exécuter fresh install, restore et uninstall sur une instance YunoHost jetable.

## M — Skills réellement utilisées

```text
arcenal-gauntlet — diagnostic, correction bornée, validation et mémoire projet — appliquée
piloter-projet-digital — matrice de recette et contrôle du périmètre — appliquée
```

Les skills externes recommandées par le CDC n'étaient pas installées. Elles n'ont été ni chargées ni déclarées comme utilisées.

## N — Verdict

```text
HARDENING REQUIRED
```

Motifs déterminants : correction HIGH non publiée, recette visuelle et fonctionnelle incomplète, automatisations non recettées, SilverBullet non configuré et cycle destructif réservé à une instance jetable.

Suite unique recommandée : `hardening supplémentaire` limité à la publication Preview de la correction puis à la levée des preuves manquantes. Aucun nouveau lot fonctionnel ne doit commencer avant cette clôture.
