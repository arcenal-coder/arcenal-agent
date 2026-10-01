# Coffre de secrets ARC

## Contrat

`ArcVault` expose uniquement cinq opérations : lire, exiger, enregistrer,
supprimer et vérifier la présence d’un secret. Les consommateurs manipulent des
références comme `OPENROUTER_API_KEY`, jamais une structure de stockage.

Le backend initial `ArcFileVault` conserve la compatibilité avec le fichier
applicatif `.env`. Ce choix évite une nouvelle dépendance ou un nouveau service
pendant l’extraction du runtime. Il pourra être remplacé par un backend chiffré
sans changer les consommateurs.

## Priorité et protection

La résolution suit cet ordre :

1. secret injecté dans l’environnement du processus ;
2. secret persistant dans `$ARCENAL_HOME/.env` ;
3. erreur métier explicite pour une lecture obligatoire.

Le répertoire est créé ou resserré en `0700`. Le fichier est remplacé
atomiquement puis forcé en `0600`. Les noms de secrets sont validés et les
valeurs vides ou démesurées sont refusées. Une rotation remplace seulement la
clé ciblée ; une suppression préserve toutes les autres.

Le dashboard ARC utilise désormais directement les routes natives du coffre.
Il ne reçoit que `configured: true/false` par clé connue ; aucune route ARC ne
retourne la valeur d’un secret. La rotation remplace atomiquement l’ancienne
valeur et la suppression rend immédiatement `has_secret` faux.

## Règles d’exposition

- le contenu du coffre n’est pas sérialisé dans une réponse HTTP ;
- les registres ne conservent que la référence du secret ;
- l’interface affiche uniquement un état configuré/non configuré ;
- les journaux, erreurs, fixtures et documents ne contiennent aucune valeur
  réelle ;
- les tests utilisent exclusivement des secrets factices.

Le format `.env` reste un détail du backend. Il ne doit plus être lu directement
par ARC Core, ARC Frugal, le dashboard ou les connecteurs.
