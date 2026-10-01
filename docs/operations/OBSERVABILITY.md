# Observabilité ARC

Le `request_id` créé par le Context Builder accompagne l'identité, le plan documentaire, ARC Frugal, les mesures et la réponse. Les traces conservent le mode d'exécution, le fournisseur, le modèle, les tokens, le coût, les latences totale/RAG/routage, la taille du contexte, les tentatives et les échecs provider.

Le health check sépare la santé d'ARC de celle des providers. Un provider distant indisponible ne rend pas l'administration, le RAG, la LDA, le wiki, la mémoire, le déterministe, le cache et les workflows locaux indisponibles.

Les journaux et audits utilisent des identifiants et des résultats synthétiques. Ils ne conservent ni clés, ni tokens, ni prompt système complet, ni contenu confidentiel complet.
