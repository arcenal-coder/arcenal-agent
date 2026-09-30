# État actuel des agents et des prompts

## Conclusion

Le logiciel possède un agent général par session et sait créer des profils
spécialisés. Il ne possède pas encore un `Agent Manager` métier central qui
sélectionne automatiquement un agent par application, mission et utilisateur.

## Agent général ARC

- ARC réutilise `AIAgent` et la boucle Hermes.
- Le plugin `arcenal-supervisor` ajoute l’identité, les capacités et les outils
  d’administration ARC au prompt général.
- Chaque session fixe provider, modèle, profil, outils, contexte et mémoire.
- La passerelle peut conserver des agents en cache par session.

## Profils spécialisés

Le volet Agents crée des profils isolés. Un profil peut porter :

- une identité et une mission ;
- un modèle principal et un modèle secondaire ;
- des compétences et outils autorisés ;
- une mémoire `profiles/<nom>/memories/MEMORY.md` ;
- ses propres paramètres et secrets selon les mécanismes Hermes.

Ces profils constituent une base réutilisable, mais aucune application ARCenal
n’est encore raccordée à un service de requête d’agent versionné.

## Sous-agents

Hermes fournit `delegate_task` et un runtime de sous-agents. Les délégations
partagent la comptabilité et peuvent être rattachées à la conversation parente.
Ce mécanisme est générique : il ne représente pas encore les futurs rôles ATS,
RH, QSSE ou Comptabilité avec leurs contrats métier.

## Sources de prompts

| Source | Rôle |
|---|---|
| `agent/prompt_builder.py` | composition générale du prompt |
| `agent/system_prompt.py` | sections statiques, identité runtime et cache |
| `AGENTS.md`, `RULES.md`, `SECURITY.md`, `TOOLS.md` | directives administrées |
| skills Markdown | procédures spécialisées chargées à la demande |
| providers mémoire | blocs de contexte et outils mémoire |
| plugin ARC | mission, outils et contraintes d’ARC |
| profil | identité, modèle, mémoire et capacités isolées |

## Permissions

Deux niveaux se superposent : les toolsets/profils Hermes et la politique ARC
pour les capacités administratives. Une présence dans le catalogue d’outils ne
suffit pas à obtenir un droit root ; l’action ARC critique exige identité,
politique, cible valide et parfois confirmation.

## Écart avec l’Agent Manager cible

Il manque un service unique qui reçoit `application + utilisateur + agent +
contexte`, résout le profil, borne le RAG et les outils, route le modèle puis
émet une preuve d’audit corrélée. Ce service doit orchestrer les briques
existantes plutôt que créer une seconde boucle agentique.
