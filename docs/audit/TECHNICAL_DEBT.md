# Dette technique observée au Lot 0

## BLOCKER

### Recette YunoHost non contenue dans ce dépôt

- **Conséquence :** installation, SSOwat, services, broker, sauvegarde et mise à
  niveau ne peuvent pas être certifiés à partir du seul dépôt applicatif.
- **Emplacement :** dépôt séparé `arcenal-coder/arcenal_ynh`.
- **Correction :** auditer le commit épinglé puis exécuter installation,
  mise à niveau, sauvegarde, restauration et désinstallation sur YunoHost stock.
- **Lot conseillé :** contrôle de diffusion du Lot 0, puis Lot 8.

### Environnement Python de validation absent sur le poste d’audit

- **Conséquence :** la suite ARC Python ne démarre pas malgré la présence des
  tests ; le runner refuse correctement l’environnement sans `pytest`.
- **Emplacement :** `scripts/run_tests.sh`, environnement local.
- **Correction :** fournir le devShell Nix ou un venv projet validé avec les
  extras de développement. Ne pas installer implicitement des dépendances.
- **Lot conseillé :** avant promotion du Lot 0.

## HIGH

### Serveur web central très volumineux

- **Conséquence :** `hermes_cli/web_server.py` concentre de nombreuses routes,
  ce qui augmente le risque de conflit lors des synchronisations Hermes.
- **Correction :** poursuivre l’extraction en `APIRouter` sans changer les URL.
- **Lot conseillé :** maintenance continue, au fil des fonctions touchées.

### Frontières ARC/YunoHost réparties entre deux dépôts

- **Conséquence :** un contrat applicatif peut diverger de sa recette systemd,
  Nginx ou broker.
- **Correction :** tests contractuels versionnés dans les deux dépôts et matrice
  de compatibilité app/paquet.
- **Lot conseillé :** Lot 1 et contrôle de chaque publication.

### RAG sans ACL de passage ni index sémantique

- **Conséquence :** recherche limitée et future exposition excessive si des
  collections métier sont ajoutées sans filtre préalable.
- **Correction :** `ContextPlan`, ACL avant recherche, index hybride dérivé.
- **Lot conseillé :** Lot 2.

## MEDIUM

### Styles historiques encore spécialisés

- **Conséquence :** certains effets décoratifs et la page wiki publique ont
  encore leur palette propre, même si les surfaces administrateur et Chat
  partagent désormais les jetons sémantiques.
- **Correction :** migrer les règles au fil des composants vers
  `arcenal-theme.css`, sans modifier le design du wiki public.
- **Lot conseillé :** maintenance UI.

### Rendu Markdown léger

- **Conséquence :** le rendu partagé couvre titres, listes, liens et code mais
  pas tout CommonMark, notamment tableaux complexes et notes de bas de page.
- **Correction :** étendre le composant partagé avec tests de sécurité ou
  adopter le renderer déjà déclaré dans le socle après étude du poids bundle.
- **Lot conseillé :** Lot 1 ou évolution du Chat.

### Métadonnées documentaires en frontmatter uniquement

- **Conséquence :** filtres et transactions deviennent coûteux avec un grand
  corpus ; une erreur isolée doit être gérée fichier par fichier.
- **Correction :** projection de métadonnées reconstruisible et migrations
  réversibles, sans remplacer les Markdown canoniques.
- **Lot conseillé :** Lot 3.

### Pièces jointes non indexées

- **Conséquence :** ARC connaît le lien et les métadonnées, pas le contenu du
  PDF ou document bureautique.
- **Correction :** extraction asynchrone, antivirus, OCR optionnel et provenance.
- **Lot conseillé :** Lots 2–3.

## LOW

### Avertissements ESLint préexistants

- **Conséquence :** 28 avertissements React masquent potentiellement de futurs
  signaux, sans erreur de compilation actuelle.
- **Correction :** réduire progressivement les effets synchrones et lectures de
  refs pendant le rendu dans des commits isolés.
- **Lot conseillé :** maintenance.

### Noms Hermes conservés dans le socle

- **Conséquence :** confusion possible pour un contributeur, mais cet héritage
  facilite les mises à jour amont et n’est pas exposé comme produit principal.
- **Correction :** documenter les frontières, éviter un renommage massif.
- **Lot conseillé :** aucune migration globale.
