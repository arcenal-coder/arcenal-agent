# Frontière du runtime conversationnel HERMES

## Périmètre observé

La configuration, le coffre, le RAG, la LDA, la mémoire d’entreprise, le
routage, le cache et les workflows appartiennent déjà à ARC. Cette carte ne les
réattribue pas à HERMES. Elle décrit uniquement les appels conversationnels qui
restent derrière la façade ARC au terme du Lot 09.

| Besoin | Fichier ARC | Import ou fonction HERMES | Entrée | Sortie | Effets de bord | État et remplaçabilité |
|---|---|---|---|---|---|---|
| Exécution d’une réponse d’agent | `arc_core/hermes_engine.py` | `hermes_cli.oneshot._run_agent` | message enrichi, modèle, fournisseur, outils, prompt système | texte, messages, métriques d’usage | appels LLM et outils, état interne HERMES | encapsulé ; remplaçable par un exécuteur ARC |
| Tool calling et résultat structuré | `arc_core/hermes_engine.py` | résultat de `_run_agent` | appels d’outils HERMES | noms d’actions et métriques bornées | dépend des outils autorisés à la session | traduction déjà limitée à `EngineOutput` |
| Sélection concrète du fournisseur | `arc_core/provider_adapter.py` | `HermesAgentEngine.execute` | `ProviderDescriptor`, modèle et `EffectiveContext` | `EngineOutput` | appel distant possible selon politique ARC | l’adaptateur ne prend aucune décision métier |
| Assemblage du moteur | `arc_core/frugal_runtime.py` | `HermesAgentEngine` | registres ARC, politique et configuration native | `FrugalAgentEngine` | création des registres locaux | point d’injection unique |
| Streaming et sessions du chat principal | `dashboard/src/index.ts` | SDK dashboard/gateway HERMES | commandes `session.*`, `prompt.submit`, événements | deltas, historique, demandes d’approbation | session et WebSocket du dashboard | non encapsulé par `AgentEngine`, à fronter au Lot 10 |
| Authentification des requêtes agents | `plugins/arcenal-supervisor/__init__.py` | `register_token_route` | routes ARC et jeton applicatif validé | accès autorisé/refusé | enregistrement de routes dans l’hôte | fournisseur ARC présent, enregistrement HERMES restant |
| Profils secondaires | `dashboard/agents_api.py` | `hermes_cli.profiles` | nom de profil borné | profil créé/supprimé | fichiers de profil HERMES | legacy, à remplacer par le registre `AgentManager` |

## Interface minimale proposée

Le futur `ArcAgentRuntime` ne doit couvrir que les besoins observés :

```python
class ArcAgentRuntime(Protocol):
    def execute(self, context: EffectiveContext, message: str) -> EngineOutput: ...
    def stream(self, context: EffectiveContext, message: str) -> Iterable[RuntimeEvent]: ...
    def interrupt(self, execution_id: str) -> None: ...
```

`EngineOutput` porte déjà la réponse, les actions et les métriques. Les appels
d’outils et les réponses structurées sont des événements/résultats de cette
exécution ; ils ne justifient pas une seconde API générique. La persistance de
session relève d’un `ArcSessionStore` séparé afin de ne pas coupler le moteur à
l’interface web.

## Cible du prochain lot

```text
Utilisateur ou application
  → ARC Core
  → ArcAgentRuntime
  → Context Builder et outils ARC
  → ARC Frugal / Model Router
  → Provider
```

Le Lot 10 devra d’abord placer le gateway de chat et `_run_agent` derrière ce
contrat, avec un adaptateur HERMES temporaire. Il ne devra réimplémenter ni RAG,
ni mémoire, ni provider registry, ni cache, ni workflow.
