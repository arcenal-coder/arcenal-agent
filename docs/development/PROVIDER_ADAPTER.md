# Contrat des fournisseurs de modèles

ARC Frugal transmet au `ProviderExecutor` un couple `provider` / `model` choisi par le Model Router. `HermesProviderAdapter` traduit la requête interne en paramètres du moteur partagé. Il ne décide ni des ACL, ni du RAG, ni de la politique d'un agent.

OpenRouter est un provider disponible et peut constituer le provider principal d'un déploiement ARCenal. ARC Core et ARC Frugal ne dépendent pas d'OpenRouter et doivent fonctionner avec tout provider conforme au contrat interne.

Le contrat représente `chat`, `streaming`, `structured_output`, `tool_calling`, `vision`, `embeddings`, `token_usage` et `cost_reporting`. Un provider ne déclare que ce qu'il sait réellement exécuter. OpenRouter, OpenAI, Gemini, Anthropic et Ollama utilisent le même contrat ; vLLM et les endpoints compatibles OpenAI sont préparés par le même registre.

L'exécuteur limite les tentatives à deux au total, produit des traces expurgées et passe au modèle suivant uniquement lorsqu'il a déjà été autorisé par le routeur. Une réponse vide ou mal formée devient une erreur applicative contrôlée. L'absence de mesure produit zéro, jamais une estimation inventée.
