# Frontières d’intégration YunoHost

Date de l’audit : 2026-10-01. Dépôt du paquet observé : `arcenal-ynh-github`,
branche `main`, version de travail `0.21.0~ynh35`.

## Conclusion

ARCenal Agent ne modifie pas le cœur YunoHost. Il utilise le format de paquet
v2, ses ressources et ses helpers pour installer une application composée de
trois services. Le paquet n’exige ni image ARCenal, ni fork YunoHost, ni patch
SSOwat, ni modification du catalogue officiel.

L’audit a supprimé une mutation globale évitable : `www-data` n’est plus ajouté
à un groupe ARCenal. Le socket HTTP de contrôle appartient directement au
groupe `www-data`, tandis que le groupe privilégié reste propre au service de
contrôle.

## Inventaire des interactions

| Fonction | Interface utilisée | Élément touché | Scope | Réversible | Interface supportée | Risque d’upgrade YunoHost |
|---|---|---|---|---|---|---|
| Déclarer l’application | `manifest.toml`, packaging v2 | Registre applicatif | YunoHost | oui | oui | faible |
| Installer les sources | ressource `sources`, `ynh_setup_source` | `/var/www/arcenal/app` | APP_LOCAL | oui | oui | faible |
| Créer l’utilisateur principal | ressource `system_user` | compte `arcenal` | APP_LOCAL | oui | oui | faible |
| Créer l’utilisateur de contrôle | `ynh_system_user_create` | compte `arcenal_control` | APP_LOCAL | oui | oui | faible |
| Installer les dépendances APT | ressource `apt` | paquets Debian déclarés | YUNOHOST_SUPPORTED | oui, géré par YunoHost | oui | faible |
| Fournir Node.js | ressource `nodejs` | runtime applicatif | YUNOHOST_SUPPORTED | oui | oui | moyen, version épinglée |
| Installer Python | `uv sync --no-dev` dans le dossier applicatif | `.venv`, `.uv`, `.local` | APP_LOCAL | oui | mécanisme applicatif | moyen |
| Stocker les données | ressource `data_dir` | `/var/www/arcenal/data` | APP_LOCAL | oui selon purge | oui | faible |
| Publier l’interface | `ynh_config_add_nginx` | fragment Nginx de l’application | YUNOHOST_SUPPORTED | oui | oui | faible |
| Protéger l’accès | ressource `permissions`, `ynh_permission_url` | permissions `main` et `wiki` | YUNOHOST_SUPPORTED | oui | oui | moyen, contrat `auth_header` |
| Propager l’identité | en-tête SSOwat `Remote-User` | requête proxifiée uniquement | YUNOHOST_SUPPORTED | oui | oui | moyen |
| Déclarer les services | `ynh_config_add_systemd` | unités `arcenal*` | YUNOHOST_SUPPORTED | oui | oui | faible |
| Déclarer le service principal | `yunohost service add` | registre de supervision | YUNOHOST_SUPPORTED | oui | oui | faible |
| Installer le broker | copie applicative | `/usr/local/sbin/arcenal-*` | APP_LOCAL dans un espace global | oui | partiellement | moyen |
| Lire l’état YunoHost | CLI `/usr/bin/yunohost` allowlistée | aucune écriture | YUNOHOST_SUPPORTED | sans objet | oui | moyen, format JSON CLI |
| Exécuter une action | broker structuré et catalogue fermé | service, diagnostic ou sauvegarde ARC | APP_LOCAL/YUNOHOST_SUPPORTED | selon action | oui | moyen |
| Sauvegarder | `ynh_backup` | données et configurations propres à ARC | YUNOHOST_SUPPORTED | oui | oui | faible |
| Restaurer | `ynh_restore_file`, helpers de configuration | éléments propres à ARC | YUNOHOST_SUPPORTED | oui | oui | moyen |

## Audit du cycle de vie

### Installation

- `APP_LOCAL` : sources, environnement Python, build web, données, comptes et
  exécutables préfixés `arcenal`.
- `YUNOHOST_SUPPORTED` : ressources APT/Node.js, permissions, fragment Nginx,
  unités systemd et registre de service.
- `GLOBAL_CHANGE` : aucun après suppression de l’adhésion de `www-data` à un
  groupe ARCenal.
- `QUESTIONABLE` : installation de `uv` par un script réseau épinglé en version
  mais non déclaré comme ressource YunoHost. À remplacer seulement si une voie
  supportée et reproductible est démontrée.

### Mise à niveau

- Remplacement complet des seules sources ARC et reconstruction des interfaces.
- Conservation du répertoire de données, migration bornée de la configuration,
  réapplication des permissions et des fragments applicatifs.
- Aucun fichier du cœur YunoHost n’est modifié.

### Suppression

- Arrêt et retrait des trois services, du compte de contrôle et des exécutables
  ARC installés dans `/usr/local/sbin`.
- Les ressources v2 restent responsables du compte principal, des répertoires,
  du port et des permissions.
- Aucune suppression récursive de chemin système n’est présente.
- Les données métier suivent le choix YunoHost de conservation ou de purge ; le
  script ne les efface jamais silencieusement.

### Sauvegarde et restauration

- La sauvegarde déclare les données persistantes, l’état du contrôle et les
  deux configurations applicatives nécessaires à une sauvegarde de cœur.
- La restauration ne touche que ces éléments et reconstruit les sources à
  partir de l’archive vérifiée du manifeste.
- Une restauration écrasante reste interdite sur le serveur principal.

## Broker privilégié

Le broker accepte un objet JSON borné, refuse les champs inconnus et traduit
chaque action en tuple de commande constant. Aucun shell arbitraire, `eval`,
`bash -c` ou `sh -c` n’est disponible.

Les actions d’écriture actuelles sont : rafraîchir le diagnostic, redémarrer un
service catalogué, créer une sauvegarde ARC, restaurer une archive ARC dont le
nom respecte le contrat, et envoyer une notification de test bornée. La
restauration est une capacité risquée : elle reste soumise à confirmation et ne
doit pas être exercée sur le serveur principal pour la seule recette.

## Classification des essais sur le serveur principal

| Classe | Essais |
|---|---|
| SAFE | lectures d’état, appels fonctionnels ARC/ATS, SSO, anti-usurpation, provider, inspection des permissions et faible charge |
| RISKY | redémarrage ARC, sauvegarde ARC et upgrade normal après vérification SSH, récupération et espace disque |
| DESTRUCTIVE | réinstallation, purge, restauration écrasante, corruption, panne disque, suppression de base ou altération globale de SSOwat/Nginx |

Les essais destructifs portent le statut **NON TESTÉ — INSTANCE JETABLE
REQUISE**.

## Réponses obligatoires

### ARCenal Agent modifie-t-il le cœur YunoHost ?

**NON.** Aucun fichier du cœur, paquet YunoHost, configuration globale Nginx,
configuration globale SSOwat ou catalogue officiel n’est modifié.

### ARCenal Agent peut-il être installé sur un YunoHost standard ?

**NON ENCORE PROUVÉ** sur une installation vierge et jetable. Le paquet est
conçu exclusivement avec les interfaces standards et l’installation actuelle
sur le serveur principal constitue une preuve partielle, pas une recette
d’installation fraîche.

### Une mise à jour YunoHost standard risque-t-elle de casser ARC ?

Les dépendances concrètes sont le packaging v2/helpers 2.1, les ressources
Node.js/APT, `auth_header` et `Remote-User`, les helpers Nginx/systemd, la CLI
JSON YunoHost et le registre de services. Aucune dépendance à un fichier source
interne ou à un monkey patch n’a été trouvée.

### ARC peut-il être retiré sans casser YunoHost ?

**NON TESTÉ** par une désinstallation réelle, car ce test serait destructif sur
le serveur principal. L’analyse statique conclut que la suppression est bornée
aux ressources ARC et n’altère plus aucun groupe global.
