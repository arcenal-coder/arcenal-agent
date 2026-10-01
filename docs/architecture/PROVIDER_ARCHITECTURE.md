# Architecture multi-fournisseurs

ARC traite séparément la capacité demandée, le modèle capable de la fournir et le fournisseur qui l'exécute. Le chemin reste `Agent → ARC Core → ARC Frugal → Model Router → Model Registry → Provider Registry → Provider Adapter`.

Le `Provider Registry` ne contient aucun secret. Il conserve l'identifiant, le type d'adaptateur, l'état d'activation, l'adresse, la référence du secret, la localisation, la juridiction, les capacités, la priorité et la santé. Le `Model Registry` référence le fournisseur par identifiant et décrit le coût, la confidentialité et les capacités du modèle.

Le routeur élimine d'abord les providers désactivés, indisponibles, interdits ou incapables. Il applique ensuite les contraintes du modèle et de l'agent. `local_only` ne possède aucun repli distant. `local_preferred` classe les modèles locaux en premier. Les replis ne contiennent que des couples modèle/fournisseur déjà admissibles.

OpenRouter est un fournisseur disponible et peut constituer le fournisseur principal d’un déploiement ARCenal. ARCenal Agent, ARC Core, ARC Frugal, Model Router et les agents restent indépendants d’OpenRouter.

Ajouter un fournisseur revient à fournir un adaptateur, une configuration, un enregistrement et ses tests. ARC Core, les agents, le RAG, le Context Builder et la mémoire d'entreprise ne changent pas.

La résolution de configuration passe par `ArcRuntimeConfiguration`. Le
fournisseur reçoit son identifiant, ses capacités, son adresse et une référence
de secret ; il ne connaît ni le JSON natif, ni `.env`, ni la configuration
HERMES. `ArcVault` résout la référence au dernier moment. Un fournisseur local
sans authentification ne déclenche aucune lecture de secret.
