# Baseline de préproduction — Lot 06

Date : 2026-09-30. Cette baseline sépare volontairement les niveaux de preuve.

## Simulation contrôlée

Les tests automatisés couvrent les quatre routes `deterministic`, `cache`, `workflow` et `llm`, le choix local, `local_only`, le fallback multi-provider, les fournisseurs désactivés ou indisponibles, la limitation de débit, les réponses vides, la rotation de jeton et le cloisonnement des identités. Les chiffres globaux sont ceux de la validation finale du checkout ; ils ne constituent pas une mesure de charge.

## Provider réel

Une génération réelle a été exécutée le 30 septembre 2026 par le chemin `ProviderExecutor → HermesProviderAdapter → HermesAgentEngine`, sans outil et avec une consigne non confidentielle.

| Mesure | Valeur observée |
|---|---:|
| Fournisseur | OpenRouter |
| Modèle demandé | `openrouter/free` |
| Appels | 1 |
| Tentatives | 1 |
| Tokens d'entrée | 13 888 |
| Tokens de sortie | 2 |
| Coût rapporté | 0 USD |
| Latence adaptateur | 5 287,29 ms |
| Réponse conforme | oui |
| Erreur fournisseur | aucune |

Le volume d'entrée inclut le socle de contexte Hermes chargé par le moteur commun. Cette observation unique prouve l'intégration, mais ne constitue ni un benchmark ni une projection de coût. Aucun autre fournisseur distant n'est annoncé comme testé sans identifiant disponible. Ollama n'était pas joignable localement pendant la recette.

## YunoHost réel

Le paquet séparé est préparé pour SSOwat, les secrets, l'upgrade et la sauvegarde/restauration. Aucune opération YunoHost n'est déclarée testée tant qu'elle n'a pas été exécutée sur une instance réelle accessible.
