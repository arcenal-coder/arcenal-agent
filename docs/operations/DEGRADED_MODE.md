# Mode dégradé

Sans provider distant, ARC conserve l'administration, la recherche documentaire, la LDA, le wiki, la mémoire d'entreprise, les règles déterministes, le cache encore valide et les workflows locaux. Un provider local admissible reste utilisable.

Si une demande exige un LLM et qu'aucun couple modèle/provider n'est admissible, ARC retourne une erreur contrôlée. `local_only` ne tente jamais de provider distant. Un échec provider autorise uniquement les fallbacks déjà filtrés par confidentialité, capacité, coût et politiques de l'agent.
