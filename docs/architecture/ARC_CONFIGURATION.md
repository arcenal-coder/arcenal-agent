# Configuration native ARC

## Objet

`ArcConfigStore` est la frontière unique entre le métier ARC et la persistance
de sa configuration. Les consommateurs ne connaissent ni le format JSON, ni la
configuration historique HERMES. Cette séparation permet de remplacer le
backend sans modifier ARC Core, ARC Frugal, les fournisseurs ou le dashboard.

Les espaces de noms autorisés sont `core`, `agents`, `providers`, `models`,
`rag`, `memory`, `automation`, `ui` et `system`. Une valeur peut être une chaîne,
un booléen, un entier, un flottant, `null`, une liste ou un objet composé de ces
types. Toute autre donnée est refusée à la frontière.

## Backend natif

`ArcNativeConfigStore` enregistre un document JSON dans
`$ARCENAL_HOME/arcenal/config.json`. Pendant la transition,
`$HERMES_HOME` est accepté si `ARCENAL_HOME` n’est pas défini. Le répertoire est
protégé en `0700`, le fichier en `0600`, et chaque écriture est atomique.

Chaque valeur possède une seule source de vérité dans le backend actif. Depuis
le Lot 09, l’absence de `ARCENAL_CONFIG_BACKEND` sélectionne `arc`. La valeur
`hermes` n’est acceptée que comme mode legacy explicite, en lecture seule et
visible dans le healthcheck. Une erreur du stockage natif est propagée : aucun
repli silencieux vers HERMES n’existe.

Avec le backend natif, la lecture suit cette priorité :

1. valeur ARC persistante ;
2. valeur HERMES copiée lors de l’activation du backend ;
3. valeur par défaut du consommateur.

Les secrets suivent une priorité différente, décrite dans
`ARC_VAULT.md`, car une variable injectée à l’exécution doit pouvoir remplacer
temporairement la valeur persistante.

## Migration HERMES

`HermesConfigAdapter` traduit en lecture seule les sections historiques utiles :

| HERMES | ARC |
|---|---|
| `model.provider` | `models.provider` |
| `model.default` | `models.default` |
| `providers.<id>` | `providers.<id>` |
| `arcenal.access_credentials` | `system.access_credentials` |
| `arcenal.general` | `ui.general` |
| `arcenal.appearance` | `ui.appearance` |
| `arcenal.onboarding` | `ui.onboarding` |
| `approvals` | `core.approvals` |

La migration est idempotente. Elle s’exécute lorsqu’un `config.yaml` historique
est détecté sans marqueur de migration. Une clé absente est copiée, une valeur identique
est comptée comme inchangée et une valeur différente produit un conflit
explicite. La valeur ARC gagne toujours ; aucune donnée historique n’est écrasée
ou supprimée silencieusement. Le marqueur `system.hermes_migration` évite de
réinitialiser HERMES Config aux démarrages suivants et ne contient aucun secret.

L’API `/configuration/v1` conserve la forme attendue par l’interface, mais lit
et écrit exclusivement `ArcConfigStore`. Les secrets passent par les routes
`/configuration/v1/secrets/{key}` et uniquement par `ArcVault`.

## Contrat des consommateurs

- ARC Frugal demande le modèle et l’état des fournisseurs à
  `ArcRuntimeConfiguration`.
- Les API du dashboard utilisent le coffre ARC pour les secrets.
- Les adaptateurs de fournisseurs reçoivent une configuration résolue et ne
  connaissent pas son stockage.
- Une API ne doit jamais renvoyer le contenu d’un secret.

Toute nouvelle lecture directe de `hermes_cli.config` hors de
`hermes_config_adapter.py` est une régression couverte par un test statique.

`HermesConfigAdapter` pourra être supprimé lorsque toutes les installations
actives auront un marqueur natif vérifié, que le mode legacy ne sera plus
utilisé et que les tests de migration des anciennes versions pourront être
conservés sans charger le runtime HERMES.
