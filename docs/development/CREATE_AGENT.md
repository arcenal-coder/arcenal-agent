# Créer un nouvel agent ARCenal

Cet exemple ajoute demain un Agent RH sans modifier ARC Core.

## 1. Définir le contrat

Créer une `AgentDefinition` avec un identifiant stable, par exemple `rh`, et
une application autorisée, par exemple `arcenal-rh`. Déclarer uniquement les
permissions, outils et scopes réellement disponibles :

```python
agent = AgentDefinition(
    id="rh",
    name="Agent RH",
    description="Assistant des processus RH autorisés.",
    role="human-resources",
    application="arcenal-rh",
    system_instructions=(InstructionBlock(id="mission", content="Respecter le périmètre RH autorisé."),),
    permissions=("rh.read",),
    tools=(),
    knowledge_scopes=("company", "rh"),
    model_policy=ModelPolicy(local_preferred=True),
    autonomy_level=AutonomyLevel.CONTROLLED,
)
```

Ne jamais placer de clé API, mot de passe ou jeton dans la définition.

## 2. Enregistrer

Appeler `AgentManager.register(agent)` depuis une migration ou une commande
d'administration contrôlée. Une seconde source de vérité ou une condition
`if agent == "rh"` dans ARC Core n'est pas nécessaire.

## 3. Fournir l'identité applicative

Créer un secret dédié d'au moins 43 caractères, l'injecter au service sous le
nom `ARCENAL_APP_ARCENAL_RH_TOKEN`, puis déclarer la route exacte dans le point
d'intégration d'authentification du plugin. Aucun secret ne doit être commité.

## 4. Tester

Ajouter les cas nominal, limite et échec : enregistrement, récupération,
application autorisée, autre application refusée, agent désactivé, permission
injectée refusée et appel complet jusqu'au moteur simulé.

Commande canonique du projet :

```text
scripts/run_tests.sh tests/test_arcenal_runtime.py tests/test_arcenal_supervisor.py tests/arcenal_security/ -q
```

Le linter, le contrôle des types, les tests frontend, le build et
`git diff --check` doivent également réussir avant livraison.
