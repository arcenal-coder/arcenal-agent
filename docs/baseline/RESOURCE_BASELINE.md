# Baseline locale de ressources — Lot 07B

Date : 2026-10-01. Mesure effectuée sur le Mac de développement avec le build
courant, un répertoire de données temporaire et une écoute locale. Ce n’est pas
une mesure du serveur YunoHost principal.

## Méthode

- démarrage de `arcenal dashboard` sur `127.0.0.1` avec le build déjà produit ;
- attente de la première réponse HTTP, puis stabilisation pendant cinq secondes ;
- dix lectures HTTP de la page d’accueil ;
- aucune conversation LLM, aucun provider distant et aucun document métier ;
- arrêt du processus après la mesure.

## Résultats observés

| Mesure | Valeur |
|---|---:|
| Temps jusqu’à la première réponse HTTP | 2 s, résolution de mesure à la seconde |
| RAM après 5 s au repos | 169 472 Kio, environ 165,5 Mio |
| CPU après 5 s au repos | 0,8 % |
| RAM après 10 lectures HTTP | 169 552 Kio, environ 165,6 Mio |
| CPU observé après les lectures | 1,7 % |
| Fenêtre des 10 lectures locales | inférieure à 1 s |
| Données initialisées temporairement | 3 936 256 octets |
| Base `state.db` initiale | 380 928 octets |
| Environnement Python local | 271 Mio, 98 distributions |
| Build web | 3,8 Mio |
| Plugin ARCenal | 1,2 Mio |

## Limites

- La RAM inclut encore le runtime Hermes historique et ses capacités générales.
- Le CPU instantané n’est pas un benchmark et varie avec la machine.
- Le test ne mesure ni une requête RAG, ni une génération LLM, ni une charge
  concurrente.
- Les permissions locales du répertoire temporaire ne prouvent pas les modes
  YunoHost ; ceux-ci sont imposés séparément par systemd et le paquet.
- La taille installée YunoHost doit être relevée sur une instance réelle après
  upgrade maîtrisé. Les `node_modules` et caches de build ne sont pas inclus
  dans le chiffre du build web.

Cette baseline sert de point de comparaison au futur ARC Native Runtime. Toute
extraction devra diminuer ou expliquer les écarts de taille, RAM et démarrage
sans dégrader les fonctions ou les tests.

## Comparaison après le Lot 08

La même méthode a été rejouée après l’extraction de la configuration et du
coffre, sur le même poste et sans appel fournisseur.

| Mesure | Lot 07B | Lot 08 | Écart observé |
|---|---:|---:|---:|
| Première réponse HTTP | 2 s | 1 s | -1 s |
| RAM au repos | 169 472 Kio | 145 600 Kio | -23 872 Kio |
| RAM après 10 lectures | 169 552 Kio | 145 808 Kio | -23 744 Kio |
| CPU au repos | 0,8 % | 1,8 % | +1,0 point |
| CPU après lectures | 1,7 % | 1,2 % | -0,5 point |
| Fenêtre de 10 lectures | < 1 s | < 1 s | stable |
| Données temporaires | 3 936 256 octets | 4 747 264 octets | +811 008 octets |
| Environnement Python | 271 Mio | 271 Mio | stable |
| Build web | 3,8 Mio | 3,8 Mio | stable |
| Plugin ARCenal | 1,2 Mio | 1,4 Mio | +0,2 Mio |

Aucune dépendance ni aucun service résident n’a été ajouté. La baisse de RAM et
de démarrage est favorable mais reste une observation locale, non un engagement
de performance. La hausse des données temporaires vient des états initialisés
par le runtime courant ; le fichier natif n’est créé qu’à la première valeur à
migrer ou enregistrer. La croissance du plugin correspond aux contrats, tests
et composants natifs du lot.

## Comparaison après le Lot 09

La méthode reste identique et utilise le backend ARC implicite, sans variable
`ARCENAL_CONFIG_BACKEND`, sans fournisseur distant et sans conversation LLM.

| Mesure | Lot 08 | Lot 09 | Écart observé |
|---|---:|---:|---:|
| Première réponse HTTP | 1 s | 1 s | stable |
| RAM au repos | 145 600 Kio | 146 256 Kio | +656 Kio |
| RAM après 10 lectures | 145 808 Kio | 146 432 Kio | +624 Kio |
| CPU au repos | 1,8 % | 1,0 % | -0,8 point |
| CPU observé juste après les lectures | 1,2 % | 5,1 % | +3,9 points transitoires |
| Fenêtre de 10 lectures | < 1 s | < 1 s | stable |
| Données temporaires | 4 747 264 octets | 4 743 168 octets | -4 096 octets |
| Environnement Python | 271 Mio | 271 Mio | stable |
| Build web | 3,8 Mio | 3,8 Mio | stable |
| Plugin ARCenal | 1,4 Mio | 1,4 Mio | stable |

L’écart mémoire reste inférieur à 1 Mio et aucun composant résident n’a été
ajouté. Le CPU après lectures est un instantané influencé par les dix requêtes
consécutives ; le temps de démarrage, la fenêtre de lecture et les tailles sont
stables.
