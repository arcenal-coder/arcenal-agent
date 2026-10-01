# Extraction de la configuration HERMES

## État après le Lot 09

Avant cette tranche, sept imports directs de `hermes_cli.config` étaient
présents dans le périmètre ARC. Un seul demeure, chargé tardivement dans
`arc_core/hermes_config_adapter.py`. Il n’est pas initialisé dans le démarrage
nominal natif et constitue uniquement la frontière de migration/diagnostic.

## Cartographie et classement

| Fichier avant extraction | Fonction | Donnée | Opération | Secret | Classe avant → après | Migration |
|---|---|---|---|---:|---:|---|
| `arc_core/frugal_runtime.py` | `_configured_model` | fournisseur et modèle | lecture | non | B → A | `ArcRuntimeConfiguration.model_selection` |
| `arc_core/frugal_runtime.py` | `_provider_enabled` | activation et clé provider | lecture | oui | B → A | configuration injectée et `ArcVault` |
| `tools.py` | `access_catalog` | comptes, API et présence du secret | lecture | oui | C → A | catalogue via configuration et coffre ARC |
| `dashboard/provider_connections_api.py` | `_configured_key` | clés OpenRouter, OpenAI, Gemini, Anthropic, Mistral et endpoints compatibles | lecture | oui | B → A | `ArcVault.get_secret` |
| `dashboard/access_connections_api.py` | `_credentials` | accès inter-applications et secrets associés | lecture | oui | C → A | `system.access_credentials` et `ArcVault` |
| `dashboard/silverbullet_api.py` | `_credential` | URL et jeton SilverBullet | lecture | oui | C → A | configuration et coffre ARC |
| `dashboard/plugin_api.py` | `_configured_openrouter_key` | clé OpenRouter | lecture | oui | B → A | `ArcVault.get_secret` |
| API générique du dashboard HERMES | écrans Paramètres ARC | configuration et secrets | lecture/écriture | mixte | D → A | API native `configuration/v1` et `ArcVault` |
| `dashboard/agents_api.py` et profils amont | chargement de profil | profil utilisateur | lecture | non | D → D | hors tranche Configuration/Vault |
| fournisseur d’authentification du dashboard | session administrateur | identité et jeton de session | lecture | oui | D → D | hors Lot 08 |

Les classes désignent : A indépendant, B encapsulé, C adaptation légère, D
dépendance profonde et E probablement inutilisé. Aucun usage E n’a été supprimé
sans preuve.

Les consommateurs migrés sont :

- ARC Frugal pour le modèle actif et l’activation des fournisseurs ;
- les connexions OpenRouter et multi-fournisseurs ;
- les comptes et API métier ;
- le connecteur SilverBullet ;
- le catalogue d’accès présenté au chat ARC.

## Stratégie de coexistence

Par défaut, `runtime_configuration()` ouvre le stockage natif et migre une fois
les installations possédant encore `config.yaml`. Les clés natives existantes
ne sont jamais remplacées. Les conflits sont journalisés sans valeur, attachés
à `ArcRuntimeConfiguration.migration` et exposés sous forme de clés dans le
diagnostic. `ARCENAL_CONFIG_BACKEND=hermes` active volontairement le mode
legacy en lecture seule.

La configuration HERMES n’est ni supprimée ni modifiée. Elle reste un filet de
compatibilité pendant que les autres surfaces du runtime sont extraites.

## Limites restantes

- le moteur conversationnel et le serveur de dashboard restent issus de
  HERMES ;
- `HERMES_HOME` demeure un repli de chemin tant que le paquet n’injecte pas
  partout `ARCENAL_HOME` ;
- la commande de modèle du runtime conversationnel reste une frontière HERMES,
  sans redevenir la source de vérité de la configuration ARC ;
- les profils, l’authentification du dashboard et le démarrage seront extraits
  dans des lots ultérieurs.

L’adaptateur sera supprimable après validation d’un cycle de migration sur les
installations actives et retrait du mode legacy explicite.
