# Matrice de recette YunoHost — Lot 07

Décision actuelle : **HARDENING REQUIRED**
Motif : aucune instance YunoHost dédiée n’est disponible pour produire les
preuves réelles obligatoires. Les contrôles locaux ne remplacent pas cette
recette.

Statuts autorisés : `PASS`, `FAIL`, `BLOQUÉ`, `NON EXÉCUTÉ`. Un statut `PASS`
exige une preuve horodatée issue de la cible dédiée.

| ID | Précondition | Action | Résultat attendu | Résultat réel | Statut | Preuve |
|---|---|---|---|---|---|---|
| YNH-ENV-01 | Cible dédiée | Collecter OS, YunoHost, CPU, RAM et disque | Baseline complète et expurgée | Cible absente | BLOQUÉ | `YUNOHOST_PREINSTALL.md` |
| YNH-INSTALL-01 | Instance propre | Installer le paquet par YunoHost | Installation sans intervention cachée | Non exécuté | BLOQUÉ | Journal YunoHost requis |
| YNH-INSTALL-02 | Installation réussie | Contrôler manifest, Nginx et permissions | Configurations conformes | Non exécuté | BLOQUÉ | États et `stat` requis |
| YNH-SVC-01 | Application installée | Vérifier les trois services | Tous actifs et enregistrés | Non exécuté | BLOQUÉ | `systemctl`, registre YunoHost |
| YNH-SVC-02 | Services actifs | Redémarrer les trois services | Retour automatique à l’état actif | Non exécuté | BLOQUÉ | Journaux requis |
| YNH-REBOOT-01 | Recette sauvegardée | Redémarrer le serveur | Aucune action manuelle nécessaire | Non exécuté | BLOQUÉ | Boot et services requis |
| YNH-PERM-01 | Installation réussie | Contrôler données, bases et secrets | `0700`/`0600` selon le contrat | Non exécuté | BLOQUÉ | Sortie `stat` requise |
| YNH-SSO-01 | Admin connecté | Ouvrir ARC | Identité admin propagée | Non exécuté | BLOQUÉ | Requête et audit requis |
| YNH-SSO-02 | Session absente | Ouvrir ARC | Redirection ou refus SSOwat | HTTP 302 vers `/yunohost/sso`, en-tête `x-sso-wat`, le 2026-10-01 | PASS | Contrôle HTTP anonyme non intrusif |
| YNH-SSO-03 | Compte hors groupe | Ouvrir ARC | Accès refusé | Non exécuté | BLOQUÉ | Réponse HTTP requise |
| YNH-SSO-04 | Client contrôlé | Forger les headers d’identité | Identité forgée ignorée | Non exécuté | BLOQUÉ | Requêtes comparées requises |
| YNH-LOGIN-01 | Premier accès admin | Parcourir les espaces ARC | Chat, Agents, RAG et Paramètres utilisables | Non exécuté | BLOQUÉ | Captures et journal requis |
| YNH-INIT-01 | Installation vierge | Vérifier registres et moteurs | ARC, ATS et registres initialisés | Non exécuté | BLOQUÉ | API et interface requises |
| YNH-AI-01 | Secret de recette | Appel OpenRouter réel | Réponse, tokens, coût, latence et `request_id` | Non exécuté | BLOQUÉ | Mesures requises |
| YNH-AI-02 | Second adapter configuré | Tester un second provider | Réel ou simulé explicitement | Non exécuté | BLOQUÉ | Résultat requis |
| YNH-OLLAMA-01 | Ollama disponible | Tester `local_preferred` | Modèle local retenu | Non exécuté | NON EXÉCUTÉ | Facultatif |
| YNH-OLLAMA-02 | Ollama disponible | Tester `local_only` | Aucun appel distant | Non exécuté | NON EXÉCUTÉ | Facultatif |
| YNH-SECRET-01 | Appel provider effectué | Inspecter les journaux | Aucun secret présent | Non exécuté | BLOQUÉ | Recherche expurgée requise |
| YNH-DATA-01 | Jeu témoin créé | Produire le snapshot | Tous les identifiants et comptes présents | Non exécuté | BLOQUÉ | Snapshot requis |
| YNH-UPGRADE-01 | Version précédente installée | Lancer un vrai upgrade | Nouvelle version active | Non exécuté | BLOQUÉ | Journal YunoHost requis |
| YNH-UPGRADE-02 | Upgrade terminé | Comparer le snapshot | Aucune perte de donnée ou secret | Non exécuté | BLOQUÉ | Comparaison requise |
| YNH-UPGRADE-03 | Scénario maîtrisé | Interrompre un upgrade | Récupération sans corruption | Non exécuté | NON EXÉCUTÉ | À évaluer sur cible |
| YNH-MIG-01 | Base ancienne disponible | Appliquer deux fois les migrations | Schéma correct et idempotent | Non exécuté | BLOQUÉ | Schéma et journaux requis |
| YNH-BACKUP-01 | Jeu témoin présent | Créer une sauvegarde YunoHost | Archive réussie et mesurée | Non exécuté | BLOQUÉ | Nom, taille, durée requis |
| YNH-RESTORE-01 | Archive valide | Restaurer sur cible propre | Application active et enregistrée | Non exécuté | BLOQUÉ | Journal YunoHost requis |
| YNH-RESTORE-02 | Restore terminé | Comparer le jeu témoin | Toutes les données retrouvées | Non exécuté | BLOQUÉ | Comparaison requise |
| YNH-RESTORE-03 | Restore terminé | Recontrôler les permissions | Modes restrictifs conservés | Non exécuté | BLOQUÉ | Sortie `stat` requise |
| YNH-INDEX-01 | Index exclus du backup | Reconstruire les index | Recherche et citations cohérentes | Non exécuté | BLOQUÉ | Mesures requises |
| YNH-SB-01 | SilverBullet dédié installé | Synchroniser puis restaurer | Pages, LDA et état conservés | Non exécuté | BLOQUÉ | Instance requise |
| YNH-E2E-ARC-01 | SSO et provider actifs | Interroger ARC avec RAG | Chaîne complète et citation correcte | Non exécuté | BLOQUÉ | `request_id` requis |
| YNH-E2E-ATS-01 | Identité ATS configurée | Interroger l’agent ATS | Scopes ATS appliqués, aucune fuite | Non exécuté | BLOQUÉ | Deux identités requises |
| YNH-FRUGAL-01 | Règle déterministe | Exécuter la requête | Aucun appel LLM | Non exécuté | BLOQUÉ | Métrique d’appel requise |
| YNH-FRUGAL-02 | Cache admissible | Répéter une requête équivalente | Second appel LLM nul | Non exécuté | BLOQUÉ | Métriques requises |
| YNH-FRUGAL-03 | Workflow témoin | Exécuter chemin normal puis exception | Local puis fallback LLM gouverné | Non exécuté | BLOQUÉ | Traces requises |
| YNH-ACL-01 | Admin et ATS disponibles | Rechercher le même corpus | Résultats conformes aux scopes | Non exécuté | BLOQUÉ | Comparaison requise |
| YNH-LDA-01 | V1 et V2 présentes | Interroger la procédure | Seule V2 applicable est utilisée | Non exécuté | BLOQUÉ | Citation requise |
| YNH-MEM-01 | Mémoire témoin | Créer, corriger, expirer, oublier | Effet immédiat sur le RAG | Non exécuté | BLOQUÉ | Store/index/cache requis |
| YNH-DOWN-01 | Provider distant actif | Couper son accès | Fonctions locales disponibles | Non exécuté | BLOQUÉ | Health et parcours requis |
| YNH-DB-01 | Sauvegarde disponible | Simuler un verrou | Message contrôlé, aucune corruption | Non exécuté | BLOQUÉ | Journal et intégrité requis |
| YNH-DISK-01 | Simulation bornée | Provoquer un échec d’écriture | Refus contrôlé, données intactes | Non exécuté | BLOQUÉ | Test sûr requis |
| YNH-OBS-01 | Requêtes variées | Contrôler les mesures | Tous les champs Lot 07 présents | Non exécuté | BLOQUÉ | Export expurgé requis |
| YNH-HEALTH-01 | Provider hors service | Interroger la santé ARC | ARC dégradé mais disponible | Non exécuté | BLOQUÉ | Réponse health requise |
| YNH-PERF-01 | Cible au repos | Mesurer quatre chemins | Baseline latence établie | Non exécuté | BLOQUÉ | Mesures requises |
| YNH-RES-01 | Cible au repos et en charge | Mesurer CPU, RAM et disque | Aucune anomalie évidente | Non exécuté | BLOQUÉ | Mesures requises |
| YNH-LOAD-01 | Jeu témoin stable | Lancer 5 à 20 requêtes | Aucun crash, lock ou fuite ACL | Non exécuté | BLOQUÉ | Rapport de charge requis |
| YNH-ROTATE-01 | Secret de recette actif | Effectuer une rotation | Ancien refusé, nouveau accepté | Non exécuté | BLOQUÉ | Deux tests requis |
| YNH-PROMPT-01 | Directives longues | Créer une nouvelle session | Identité et sections ARC chargées | Test local réussi, YNH absent | BLOQUÉ | Test unitaire local disponible |
| YNH-CONTEXT-01 | Gros corpus autorisé | Construire le contexte | Budget respecté sans fuite ACL | Non exécuté | BLOQUÉ | Mesures requises |

## Synthèse obligatoire

| Domaine | Décision actuelle |
|---|---|
| Installation | FAIL — non prouvée sur cible dédiée |
| Upgrade | FAIL — non prouvé sur cible dédiée |
| Restart | FAIL — non prouvé sur cible dédiée |
| Reboot | FAIL — non prouvé sur cible dédiée |
| SSO | FAIL — non prouvé sur cible dédiée |
| Backup | FAIL — non prouvé sur cible dédiée |
| Restore | FAIL — non prouvé sur cible dédiée |
| Provider | FAIL — non prouvé depuis YunoHost |
| ACL | FAIL — non prouvé avec identités réelles |
| `local_only` | FAIL — non prouvé depuis YunoHost |

Dans cette synthèse, `FAIL` signifie que le critère de sortie du Lot 07 n’est
pas satisfait ; il ne prétend pas qu’un essai réel a échoué.

## Condition de Release Candidate

La décision ne pourra devenir **READY FOR RELEASE CANDIDATE** qu’après passage
réel des critères bloquants, correction des anomalies `BLOCKER` et `HIGH`, puis
rejeu complet sur la même révision du paquet et de l’application.
