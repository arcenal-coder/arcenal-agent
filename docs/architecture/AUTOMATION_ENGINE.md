# Automation Engine

Un workflow est versionné, persistant et possède un statut parmi `draft`, `testing`, `active`, `disabled`, `archived`. Il ne devient actif qu'après le passage en test et une approbation humaine identifiée.

L'exécuteur vérifie que les permissions et outils du workflow sont des sous-ensembles du contrat de l'agent. Il n'élève jamais ses propres droits. Les niveaux d'autonomie existants `automatic`, `controlled` et `approval_required` sont réutilisés.

Les opérations déterministes du Lot 05 lisent une valeur structurée, produisent un gabarit ou un statut. Une donnée absente constitue une exception et rend la main à ARC Frugal, qui peut solliciter un LLM autorisé.
