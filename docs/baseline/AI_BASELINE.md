# Baseline IA avant ARC Frugal

Date d’audit : 30 septembre 2026.

## Portée

Le Lot 0 n’effectue aucun appel payant ou contenant des données réelles. Aucune
clé provider n’a été lue et aucune conversation utilisateur n’a été exportée.
Cette baseline fixe donc le contrat de mesure déjà opérationnel et distingue
les valeurs disponibles des mesures de production encore à collecter.

## Mesures disponibles par appel

Le point canonique se trouve dans `agent/conversation_loop.py` après chaque
réponse provider :

| Mesure | Source | Persistance |
|---|---|---|
| provider et modèle | runtime de l’agent | log technique + `state.db` |
| tokens entrée/sortie | réponse normalisée | compteurs session + `session_model_usage` |
| tokens de cache | réponse normalisée | compteurs session + SQLite |
| tokens de raisonnement | réponse normalisée | compteurs session + SQLite |
| coût estimé | `agent/usage_pricing.py` | SQLite, statut et source du tarif |
| durée | chronométrage de l’appel | log et historique de latence en mémoire |
| nombre d’appels | boucle de conversation | session SQLite |
| taille de contexte | tokens prompt du provider, sinon estimation | moteur de contexte |
| session/tâche | identifiants internes | tables de session et usage |

Les appels auxiliaires utilisent le même contexte de comptabilité et sont
attribués à la session et à la tâche lorsque leur provider retourne l’usage.

## Valeurs de référence du Lot 0

| Indicateur | Valeur constatée | Commentaire |
|---|---:|---|
| Appels LLM lancés par l’audit | 0 | aucune consommation volontaire |
| Temps moyen d’une requête standard | non mesuré | exige une recette avec provider et modèle fixés |
| Modèle de référence | non fixé | configurable par installation |
| Tokens moyens entrée/sortie | non mesurés | les compteurs existent, pas d’échantillon neutre local |
| Taille moyenne de contexte | non mesurée | disponible après réponses provider |
| Tests frontend | 403 réussis en 2,23 s avant modification | mesure de santé, pas performance LLM |

## Protocole de mesure pour les lots suivants

1. Fixer version, provider, modèle, température, profil et corpus.
2. Utiliser un jeu de requêtes expurgé : question simple, diagnostic serveur en
   lecture, recherche documentaire et tâche avec deux outils.
3. Exécuter au moins dix répétitions par scénario hors échauffement.
4. Exporter uniquement des agrégats : moyenne, médiane, p95, tokens, appels,
   cache, coût et taux d’erreur.
5. Ne jamais exporter prompts, réponses, clés, noms de personnes ou documents.
6. Comparer chaque optimisation à cette configuration figée et non à un autre
   modèle ou un autre corpus.

## Critères ARC Frugal à suivre

- tokens d’entrée et coût par réponse utile ;
- p95 de latence et taux d’indisponibilité ;
- proportion de cache lu ;
- nombre d’appels et d’outils par tâche ;
- qualité des citations RAG ;
- taux d’escalade vers un modèle plus coûteux.
