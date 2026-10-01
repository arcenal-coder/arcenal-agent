# ARC Core

## Responsabilité

ARC Core est le point de passage commun des requêtes adressées aux agents
ARCenal. Il ne remplace pas Hermes : il résout l'agent, construit son contexte
effectif, délègue l'inférence au moteur Hermes existant et relie le résultat au
journal d'audit ARCenal.

Le code réside dans `plugins/arcenal-supervisor/arc_core`. Cette position garde
la spécialisation ARC hors du cœur amont et limite les conflits de mise à jour.

## Flux exécuté

1. `AgentManager` résout un identifiant stable et refuse un agent inconnu ou
   désactivé.
2. `ContextBuilder` vérifie l'application, retire les permissions interdites,
   construit le `ContextPlan` et récupère les seuls chunks autorisés.
3. `ArcCore` crée l'identité de requête, journalise le début et délègue à ARC
   Frugal.
4. ARC Frugal tente une règle, un cache sûr ou un workflow validé. Lorsque le
   LLM reste nécessaire, Model Router choisit la capacité minimale autorisée
   et `HermesAgentEngine` appelle la boucle one-shot existante.
5. `ArcCore` renvoie une enveloppe sans secret avec citations structurées et
   journalise durée, outils, métriques RAG et usage provider.

Le moteur reste injecté derrière le protocole `AgentEngine`. ARC Frugal
enveloppe l'adaptateur Hermes sans modifier la boucle fournisseur amont.

La configuration suit la même inversion de dépendance. ARC Core et ARC Frugal
consomment `ArcConfigStore` et `ArcVault` via `ArcRuntimeConfiguration` ; seul
`HermesConfigAdapter` lit encore le format historique. Les clés ARC natives ont
priorité et les divergences de migration sont signalées sans écrasement.

## Garanties

- aucune permission ou instruction système n'est acceptée dans le payload ;
- le contexte applicatif est borné et présenté au modèle comme donnée non
  fiable ;
- une politique agent complète la politique globale sans la remplacer ;
- l'utilisateur reste `null` lorsqu'aucune identité n'est fournie ;
- les validations et approbations existantes des outils Hermes restent actives.
- les sources renvoyées proviennent du RAG, jamais du texte libre du modèle.

## Persistance

Les définitions sont enregistrées atomiquement dans
`$HERMES_HOME/arcenal/agents.json`, avec un mode `0600`. Ce fichier est la
source de vérité du lot 01, est sauvegardable avec les données ARCenal et peut
être migré ultérieurement vers SQLite sans modifier les consommateurs grâce à
`AgentRepository`.

La configuration native réside dans `$ARCENAL_HOME/arcenal/config.json` quand
le backend `arc` est activé. Le backend `hermes` reste le choix transitoire par
défaut tant que les écritures du panneau existant ne sont pas toutes migrées.
Le coffre conserve temporairement le fichier `$ARCENAL_HOME/.env` pour rester
compatible avec les installations YunoHost existantes. `HERMES_HOME` n’est
qu’un repli transitoire quand `ARCENAL_HOME` n’est pas injecté.
