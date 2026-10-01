# Mémoire d’entreprise ARCenal

## Rôle

La mémoire d’entreprise conserve des informations utiles à la continuité du travail sans leur conférer l’autorité d’un document officiel. Elle est distincte de l’historique du chat, de la LDA et du wiki.

La source de vérité est `enterprise-memory.sqlite3`, dans le répertoire de données privé d’ARCenal. L’index du Knowledge Engine n’est qu’une projection reconstruisible.

## Modèle

Une mémoire possède un identifiant stable, un type, un résumé, un contenu, une provenance, un niveau de confiance, un statut, une politique de conservation, des ACL et un numéro de version.

Types initiaux : `fact`, `decision`, `person`, `project`, `rule` et `preference`.

Les champs spécialisés couvrent les motifs et décideurs, les rôles professionnels, les statuts de projet, la nature des règles, le contexte des préférences et les relations typées. Les informations RH sensibles restent dans leur application métier.

## Relations

Les relations sont des triplets `relation_type`, `target_kind`, `target_id` conservés avec l’entrée. Ce contrat permet les liens personne-projet, décision-document ou préférence-personne sans imposer un graphe complet.

## Compatibilité

L’ancien fichier `MEMORY.md` reste lisible par les parcours historiques. Il n’est pas converti automatiquement, afin d’éviter de donner une provenance artificielle à des entrées anciennes.
