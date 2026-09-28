# Matrice de recette — ARCenal Agent 2.0

Cette matrice relie chaque critère approuvé à une preuve automatisée et à la
recette à exécuter sur une installation YunoHost. Les tests nommés sont lancés
avant chaque publication du paquet stable.

| Critère | Preuve automatisée | Recette YunoHost |
|---|---|---|
| `AC-ARC-01` | `chat-state.test.ts`, routage `/` vers `/chat` | L’ouverture de la tuile affiche le chat ARC. |
| `AC-ARC-02` | `chat-state.test.ts`, tests fournisseurs et sessions | Envoyer un message, simuler une erreur fournisseur, reprendre la conversation. |
| `AC-ARC-03` | `test_policy.py`, `test_audit.py`, tests du chat plugin | Demander un diagnostic, confirmer une réparation, vérifier son résultat et l’audit. |
| `AC-AGT-01` | `arcenal-agents.test.ts`, `test_agents_api.py` | Créer un agent puis recharger le volet Agents. |
| `AC-AGT-02` | `arcenal-agent-service.test.ts`, `test_agents_api.py` | Modifier mission, modèles, compétences, outils et mémoire isolée. |
| `AC-RAG-01` | tests connaissance, LDA, pièces jointes et workflow | Déposer un document, l’éditer, le relier et le rechercher. |
| `AC-RAG-02` | `test_knowledge_workflow.py`, tests LDA/wiki | Publier une version Applicable et vérifier LDA et wiki. |
| `AC-RAG-03` | `test_knowledge_api.py`, tests recherche documentaire | Interroger ARC et contrôler référence, version, statut et extrait. |
| `AC-SET-01` | `arcenal-settings-tabs.test.ts` et tests de chaque panneau | Parcourir les onze sections et vérifier la persistance. |
| `AC-AI-01` | tests fournisseurs, statuts et API de secrets | Connecter deux fournisseurs, les tester et changer de modèle. |
| `AC-ACC-01` | `arcenal-access.test.ts`, `test_access_connections_api.py` | Tester, limiter puis désactiver un accès métier. |
| `AC-SEC-01` | `test_policy.py`, `test_toolset.py` | Vérifier lecture, action encadrée, confirmation et refus. |
| `AC-SEC-02` | `test_approvals.py`, `test_audit.py` | Confirmer une action critique, rejouer le jeton et contrôler son refus. |
| `AC-YH-01` | `test_system_api.py`, `test_toolset.py` | Comparer la vue Système aux informations YunoHost. |
| `AC-BKP-01` | tests paquet `backup`, `restore`, source et mise à niveau | Installer, sauvegarder, restaurer puis mettre à niveau avec les données conservées. |
| `AC-UX-01` | tests d’en-tête et contrôle visuel clair/sombre | Vérifier trois volets principaux et Paramètres secondaire. |
| `AC-UP-01` | surveillance amont hebdomadaire et architecture plugin | Détecter une version Hermes, préparer une branche et rejouer toute la recette. |

Une recette serveur n’est validée que lorsque l’installation en ligne utilise
le commit et l’archive indiqués par le catalogue stable.
