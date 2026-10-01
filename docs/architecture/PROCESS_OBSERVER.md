# Process Observer

Process Observer enregistre une empreinte technique de l'agent, des outils et des clés d'entrée, ainsi qu'une signature du résultat. Il ne conserve pas de raisonnement interne.

Après un seuil configurable d'observations semblables, il crée ou actualise un `AutomationCandidate`. Le candidat contient le nombre d'observations, les entrées, les sorties, les exceptions, la confiance et le risque. L'économie reste à zéro tant qu'elle n'est pas mesurée.

L'observateur ne crée et n'active aucun workflow. La revue, le test et l'approbation restent des actions humaines distinctes.
