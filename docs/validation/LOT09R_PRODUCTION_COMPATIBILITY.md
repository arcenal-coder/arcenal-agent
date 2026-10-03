# Lot 09R — Compatibilité de production YunoHost

Date de recette : 2026-10-03

Branche locale : `arcenal`

Environnement : YunoHost principal `mail.onyx-ingenierie.com`

Application publique : `https://onyx-ingenierie.com/arcenal/`

## Verdict

```text
READY FOR LOT 10
```

La candidate historique `0.21.0~ynh36` décrite dans le premier protocole LOT
09R a été remplacée par plusieurs correctifs preview. Le serveur exécutait déjà
la candidate `0.21.0~ynh53` au début de cette reprise. Aucune rétrogradation n'a
été tentée : la recette a porté sur cette version supérieure, dont les
révisions correspondent exactement au dépôt source, au paquet YunoHost et au
catalogue preview.

Le canal stable n'a pas été modifié. Aucun fresh install, uninstall, restore,
redémarrage complet du serveur ou changement global de Nginx/SSOwat n'a été
effectué.

## A. Versions prouvées

| Composant | Version ou révision réelle |
|---|---|
| Application ARCenal | `0.21.0-arcenal35` |
| Tag source | `v0.21.0-arcenal35` |
| Révision source | `ff93c4c59f4307274163a264a94e44473b0ca2d0` |
| Paquet YunoHost | `0.21.0~ynh53` |
| Révision package | `b1e10a61bff97d7c6d06afbdeb6f4bb4b568d92a` |
| Révision catalogue preview | `9768e38db5944bbc659980071497745818d61850` |
| YunoHost | `12.1.40.1` stable |
| YunoHost Admin | `12.1.15` |
| SSOwat | `12.1.1` |

La révision source exposée par `arcenal.service` correspond à la tête locale et
au tag. Le catalogue preview annonce le paquet `ynh53` et la révision package
ci-dessus. Le serveur dispose de 622 Gio libres sur 934 Gio.

## B. Sauvegarde et mise à jour

```text
PASS
```

- La version installée provient de la voie YunoHost preview normale.
- L'état installé correspond exactement aux révisions publiées ; aucune copie
  manuelle de sources n'a été utilisée.
- Une sauvegarde pré-recette a été créée avec succès :
  `arcenal-lot09r-current-20261003`, 221 527 977 octets.
- Aucun restore n'a été tenté.

## C. ARC Native

```text
backend = arc
migration = complete
vault = ready
```

La migration rapporte sept valeurs copiées, aucune valeur inchangée et aucun
conflit. La configuration native conserve les espaces `core`, `models`,
`providers`, `system` et `ui`. Gemini et OpenRouter sont configurés et leurs
secrets sont présents dans le coffre sans avoir été affichés.

## D. Hermes Config

```text
chargé en nominal : NON
```

Après un redémarrage réel, le runtime installé retourne toujours
`backend=arc`, `migration=complete` et `vault=ready`. Le service ne définit pas
de repli legacy et aucun message de fallback n'apparaît dans les journaux.
L'adaptateur `HermesConfigAdapter` reste limité au mode legacy explicite et à
la migration initiale.

## E. Fonctionnel

| Fonction | État | Preuve réelle |
|---|---:|---|
| Paramètres ARC | PASS | écriture, lecture, restart, relecture puis suppression d'une sonde non sensible |
| Vault | PASS | création, rotation et suppression d'un secret de recette ; coffre final en `0600` |
| Providers | PASS | Gemini et OpenRouter configurés, secrets résolus par ARC Vault |
| OpenRouter réel | PASS | HTTP 200, modèle gratuit, 16 tokens en entrée, 8 en sortie, coût nul, 0,892 s |
| Model Router ARC | PASS | ARC résout `hermes-current` vers `gemini-3-flash-preview` |
| ARC E2E | PASS | une requête corrélée traverse Agent Manager, Context Builder, RAG documentaire, Enterprise Memory, ARC Frugal, Model Router et Gemini ; deux sources distinctes et une réponse sont présentes |
| Historique ARC | PASS | conversation de recette persistée puis archivée sans toucher aux conversations existantes |
| ATS | PASS | agent actif ; requête réelle, réponse présente, portées exactes `ats`, `company`, `recruitment` |
| Cloisonnement ATS | PASS | la même requête sélectionne la source ATS ; source finance restreinte et contenu interdit absents des sources et de la réponse |
| RAG | PASS | note Applicable temporaire indexée et retrouvée avec source et portée `company` |
| LDA | PASS | note Applicable présente dans la LDA pendant le test |
| Wiki | PASS | même version Applicable publiée dans la vue wiki pendant le test |
| Enterprise Memory | PASS | création, lecture, correction version 2, historique et suppression physique de la sonde |
| Frugal déterministe/cache/workflow | PASS tests package | contrats du runtime exact validés par la suite ciblée publiée avec la candidate |
| `local_only` | PASS tests package | registre sans modèle local rejeté avant tout appel distant |

Toutes les sondes temporaires de configuration, RAG, ATS et mémoire ont été
supprimées. L'index de connaissances a été reconstruit après nettoyage.

### Parcours corrélés ARC et ATS

Le parcours ARC a été exécuté sous l'utilisateur système `arcenal`, avec le
même environnement que le service. Une requête unique a sélectionné deux
sources temporaires identifiables : un document Applicable et une entrée
Enterprise Memory. L'audit porte le même identifiant de requête depuis la
recherche RAG jusqu'à `agent.query.completed`. ARC Frugal a produit un plan,
le Model Router a choisi Gemini, cinq appels ont été comptabilisés et la
conversation finale contient les rôles `user` et `assistant`.

Le parcours ATS a également été exécuté sous `arcenal`. Une source de
recrutement autorisée a été sélectionnée, tandis qu'une source finance
restreinte n'apparaît ni dans les citations ni dans la réponse. ARC Frugal a
routé l'exécution vers Gemini, trois appels ont été comptabilisés et la réponse
est présente. Les quatre sondes documentaires et mémoire ont ensuite disparu
du coffre et de l'index reconstruit.

### Appel OpenRouter borné

```text
provider = openrouter
HTTP = 200
request_id = gen-1791016269-1UBLi3EuYUsOBFBpzokc
model = apodex/apodex-1.1-mini:free
tokens input = 16
tokens output = 8
cost = 0
latency = 0,892 s
```

Le prompt ne contenait aucune donnée de production et demandait uniquement une
réponse courte. La clé n'a été ni affichée ni journalisée.

## F. Système

| Contrôle | État | Résultat réel |
|---|---:|---|
| Restart ARCenal seul | PASS | PID `22190` remplacé par `42011`, service actif |
| Santé après restart | PASS | HTTP 200 sur `/api/health`, 2,2 ms |
| Persistance | PASS | valeur A conservée après restart puis valeur initiale restaurée |
| Data dir | PASS | `0700 arcenal:arcenal` |
| Configuration sensible | PASS | `0600 arcenal:arcenal` |
| Vault `.env` | PASS | `0600 arcenal:arcenal` |
| Agents et conversations | PASS | fichiers `0600 arcenal:arcenal` |
| Base mémoire | PASS | `0600 arcenal:arcenal`, `PRAGMA quick_check = ok` |
| Base sessions | PASS | `0600 arcenal:arcenal`, `PRAGMA quick_check = ok` |
| Audit | PASS | dossier `0700`, journal `0600` |
| UMask | PASS | `0077` |
| Logs sans secret | PASS | deux valeurs réelles recherchées, zéro correspondance dans journal et audit |
| SSO anonyme | PASS | HTTP 302 vers `/yunohost/sso` |
| Faux `Remote-User` local | PASS | HTTP 401, aucune usurpation possible |
| Core YunoHost | PASS | aucun patch du cœur, de SSOwat ou de Nginx global par cette recette |

Les journaux du service ne contiennent aucune alerte depuis le restart. La
ligne `Hermes Web UI` au démarrage appartient encore au moteur commun conservé
par ARCenal ; elle ne constitue pas un chargement du backend Hermes Config.

## G. Ressources

| Mesure | Valeur |
|---|---:|
| RAM avant restart | 256 487 424 octets |
| RAM juste après restart | 144 941 056 octets |
| RAM stabilisée | 139 706 368 octets |
| CPU au repos après recette | 0,5 % |
| Premier contrôle HTTP après restart | 2,2 ms |
| 10 contrôles HTTP concurrents | HTTP 200, 2,6 à 7,4 ms |
| Erreurs pendant charge légère | 0 |
| Alertes systemd après charge | 0 |

La charge légère n'a produit ni erreur HTTP, ni blocage SQLite, ni arrêt du
service. Il n'existe pas de mesure comparable antérieure à l'installation de
`ynh53` : les valeurs « avant » et « après » désignent ici le restart contrôlé,
pas une comparaison entre deux versions du paquet.

## H. Bugs et observations

| ID | Sévérité | État | Cause et traitement |
|---|---|---|---|
| LOT09R-OBS-01 | LOW | OUVERT surveillé | SQLite système 3.40.1 est antérieur aux versions corrigeant le défaut WAL-reset. Le runtime détecte ce cas et impose `journal_mode=DELETE`, les deux bases contrôlées répondent `ok`. Aucun contournement système ni mise à jour hors YunoHost n'a été tenté. |

Aucun BLOCKER, HIGH ou MEDIUM n'est ouvert à l'issue de la recette.

## I. Synthèse

```yaml
Backend ARC serveur : PASS
Hermes Config absent démarrage nominal : PASS
Restart service : PASS
Persistance : PASS
Permissions : PASS
Logs sans secret : PASS
ARC réel : PASS
ATS réel : PASS
Parcours ARC corrélé RAG / mémoire / Frugal / routeur / provider : PASS
Cloisonnement ATS sur requête réelle : PASS
RAG / LDA / Wiki : PASS
Enterprise Memory : PASS
OpenRouter réel : PASS
Version Lot 09 réellement déployée : OUI — candidate corrective ynh53
```

```text
READY FOR LOT 10
```

La candidate reste dans le canal preview. Toute promotion stable exige une
instruction explicite distincte.
