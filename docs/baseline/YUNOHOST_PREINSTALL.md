# Baseline YunoHost avant installation — Lot 07

Statut : **NON EXÉCUTÉ — instance YunoHost dédiée absente**
Date de préparation : 1er octobre 2026
Interdiction : cette recette ne doit pas être exécutée sur une instance client
ou de production.

## Identification de la cible

| Élément | Valeur réelle | Preuve |
|---|---|---|
| Nom de la cible de recette | À renseigner | `hostname --fqdn` |
| Domaine de test | À renseigner | Domaine réservé à la recette |
| YunoHost | À mesurer | `yunohost --version` |
| Debian | À mesurer | `/etc/os-release` |
| Architecture | À mesurer | `dpkg --print-architecture` |
| CPU | À mesurer | `lscpu` |
| RAM | À mesurer | `free -h` |
| Disque disponible | À mesurer | `df -h / /var/www` |
| Date et heure UTC | À mesurer | `date --utc --iso-8601=seconds` |

Les sorties brutes contenant un domaine privé, une adresse personnelle, un
utilisateur ou un jeton ne doivent pas être ajoutées au dépôt. La preuve
versionnée doit être expurgée et référencer le journal de recette conservé dans
l’espace sécurisé du projet.

## État système initial

Collecter avant l’installation :

```bash
yunohost service status --output-as json
yunohost app list --output-as json
yunohost diagnosis show --issues --output-as json
ss -lntup
df -h / /var/www /var/lib
systemctl is-active nginx
systemctl is-active slapd
systemctl is-active redis-server
python3 --version
node --version || true
```

Résumer les résultats sans copier de secrets :

| Contrôle | Résultat réel | Statut |
|---|---|---|
| Services YunoHost critiques | À renseigner | NON EXÉCUTÉ |
| Ports déjà utilisés | À renseigner | NON EXÉCUTÉ |
| SSOwat actif | À renseigner | NON EXÉCUTÉ |
| Espace libre compatible avec 2 Gio | À renseigner | NON EXÉCUTÉ |
| Python compatible | À renseigner | NON EXÉCUTÉ |
| Node fourni par YunoHost | À renseigner | NON EXÉCUTÉ |
| Diagnostic sans blocage préalable | À renseigner | NON EXÉCUTÉ |

## Comptes de recette

Préparer uniquement des identités fictives dédiées :

- un administrateur YunoHost autorisé à ARC ;
- un utilisateur YunoHost non administrateur autorisé au wiki ;
- un utilisateur YunoHost non autorisé ;
- une identité applicative ATS de test, distincte des utilisateurs humains.

Ne jamais inscrire leurs mots de passe, clés, cookies ou jetons dans ce fichier.

## Critère de départ

La recette peut commencer uniquement lorsque :

- la cible est dédiée et sauvegardable ;
- son propriétaire autorise installation, suppression, reboot et restauration ;
- aucun service client ne dépend de cette cible ;
- un accès administrateur et une console de récupération sont disponibles ;
- l’espace disque est suffisant pour l’application et deux sauvegardes ;
- le commit du paquet et le tag applicatif à tester sont figés.
