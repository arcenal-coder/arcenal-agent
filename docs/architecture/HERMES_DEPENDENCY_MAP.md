# Cartographie des dépendances Hermes

Date : 2026-10-01. Cette cartographie décrit le code réellement observé après
la bascule native du Lot 09. Elle ne demande ni suppression de HERMES ni
réécriture du runtime conversationnel.

Classes :

- **A** — capacité déjà possédée par ARCenal ;
- **B** — dépendance Hermes encapsulée derrière une frontière ARC ;
- **C** — dépendance directe encore à encapsuler ;
- **D** — dépendance Hermes encore indispensable au fonctionnement ;
- **E** — candidate à suppression après preuve d’inutilité.

## Carte

| Fonction | Fichier ou surface | Classe | Interface ARCenal actuelle | Remplacement futur |
|---|---|---:|---|---|
| Contrats d’agents et registre | `arc_core/models.py`, `manager.py`, `repository.py` | A | `AgentManager` | aucun |
| Context Builder, ACL, RAG et LDA | `arc_core/context.py`, `knowledge_*` | A | `ContextBuilder`, `KnowledgeRuntime` | aucun |
| Mémoire d’entreprise | `arc_core/memory_*` | A | contrats de mémoire gouvernée | aucun |
| ARC Frugal, cache et workflows | `arc_core/frugal_*`, `automation_engine.py` | A | `FrugalAgentEngine` | aucun |
| Routage modèle/fournisseur | `model_router.py`, `provider_*` | A | `ModelRouter`, `ProviderExecutor` | aucun |
| Exécution conversationnelle | `arc_core/hermes_engine.py` | B/D | protocole `AgentEngine` | runtime ARC natif implémentant le même protocole |
| Adaptation fournisseur | `arc_core/provider_adapter.py` | B | `ProviderAdapter` | adaptateurs ARC natifs, fournisseur par fournisseur |
| Construction du runtime | `arc_core/frugal_runtime.py` | B/D | `ArcRuntimeConfiguration` injectée | fabrique ARC injectant le moteur choisi |
| Enregistrement du plugin et des outils | `plugins/arcenal-supervisor/__init__.py` | B/D | manifeste et hooks du plugin | hôte ARC natif conservant les contrats d’outils |
| Format de résultat des outils | `plugins/arcenal-supervisor/tools.py` | C | schémas d’outils ARC | type `ToolResult` ARC indépendant |
| Configuration et coffre `.env` | `arc_core/configuration*.py`, `vault.py` | A | `ArcConfigStore`, `ArcVault` natifs par défaut | backend de coffre renforcé si nécessaire |
| Lecture de configuration HERMES | `arc_core/hermes_config_adapter.py` | B | compatibilité/migration explicite en lecture seule | suppression après migration YunoHost prouvée |
| Authentification du dashboard | `arc_core/app_auth_provider.py` | C/D | identité YunoHost validée côté ARC | fournisseur d’identité ARC branché sur SSOwat |
| Route de jeton dashboard | `plugins/arcenal-supervisor/__init__.py` | B/D | enregistrement central du plugin | middleware ARC natif |
| Profils Hermes | `dashboard/agents_api.py` | C | Agent Manager ARC | registre ARC unique sans profil Hermes |
| Répertoire `HERMES_HOME` | plusieurs API du dashboard et `capabilities.py` | C | répertoire de données du paquet | `ARCENAL_HOME` résolu par un adaptateur transitoire |
| Démarrage du dashboard | unité systemd, commande `arcenal dashboard` | D | façade ARC construite | serveur ARC natif |
| Shell et composants web communs | application web amont | D | routes ARC et thème produit | extraction progressive des seules briques utilisées |
| Affichage de version Hermes | `dashboard/plugin_api.py` | E | vue de diagnostic | version runtime ARC, Hermes relégué aux composants |
| Libellés historiques Hermes | textes et métriques transitoires | E | terminologie ARC | suppression après migration des consommateurs |

## Frontière cible

```text
Interface ARC
    ↓
Adaptateur Hermes temporaire
    ↓
Runtime Hermes
```

Les composants nouveaux doivent dépendre des protocoles `AgentEngine`,
`ProviderAdapter`, du Context Builder et des registres ARC. Ils ne doivent pas
importer une nouvelle API interne Hermes lorsque cette frontière suffit.

## Écarts prioritaires

1. Le moteur concret reste créé par ARC Frugal derrière l’adaptateur Hermes.
2. L’authentification et le démarrage du dashboard reposent encore sur les
   composants Hermes.
3. Le profil d’agent secondaire dépend encore de `hermes_cli.profiles`.
4. `HERMES_HOME` reste un repli de chemin pendant la transition du paquet.

## Dépendances restantes par catégorie

| Catégorie | Dépendance restante | Frontière ARC | Prochaine action |
|---|---|---|---|
| configuration | `HermesConfigAdapter` seulement en migration/legacy | `ArcConfigStore` et `ArcVault` nominaux | retirer après preuve de migration du parc |
| conversation/runtime | `_run_agent`, gateway de sessions et streaming | `AgentEngine`, `EngineOutput`, ARC Frugal | introduire `ArcAgentRuntime` au Lot 10 |
| dashboard/bootstrap | commande `arcenal dashboard`, SDK plugins | routes et UI ARC | isoler le bootstrap après la frontière runtime |
| authentication | `register_token_route`, session dashboard | `ArcenalApplicationProvider` et SSO YunoHost | fournir un middleware ARC natif |
| profiles | `hermes_cli.profiles` pour certains agents secondaires | `AgentManager` | migrer les derniers profils vers le registre ARC |
| autres | `HERMES_HOME`, version et capacités historiques | `ARCENAL_HOME`, catalogue ARC | retirer après audit d’usage ciblé |

La configuration est **NATIVE ARC** sur le chemin nominal. Sept imports directs
ont été ramenés à l’unique adaptateur `HermesConfigAdapter`, chargé uniquement
pour une migration détectée ou un mode legacy explicite. La frontière
conversationnelle détaillée figure dans `HERMES_RUNTIME_BOUNDARY.md`.

Ces écarts justifient une extraction incrémentale. Ils ne justifient pas une
réécriture globale ni l’ajout d’un framework d’agents.
