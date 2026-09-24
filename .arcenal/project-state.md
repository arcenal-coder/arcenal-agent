# État du projet ARCenal Agent

Dernière mise à jour : 2026-09-24

Branche : `arcenal`

## Objectif courant

Livrer ARCenal Agent comme produit YunoHost autonome à trois volets — ARC,
Agents et RAG & LDA — sans exposer le tableau de bord Hermes comme interface
principale, tout en conservant Hermes comme moteur amont actualisable. Un accès
secondaire Paramètres permet à l'administrateur de connecter plusieurs moteurs
IA et de régler l'autonomie d'ARC sans créer un quatrième volet métier.

## État observé

- L'ancien tableau de pilotage est remplacé dans la navigation par trois
  espaces ARC, Agents et RAG & LDA ; le contrôle visuel est validé.
- Le plugin `arcenal-supervisor` expose l’état système, les rapports et trois
  réparations strictement autorisées, ainsi qu’un pont local en lecture vers
  les données natives YunoHost.
- Le paquet natif est maintenu séparément dans `arcenal_ynh`.
- AACP/1 est documenté, mais aucun connecteur applicatif n’est encore livré.
- Une modification utilisateur hors périmètre existe dans
  `contributors/emails/agent@agents-Mac-mini.local` et doit rester intacte.

## Décisions actives

- Hermes reste le moteur technique interne ; ARC est l’identité publique et le
  comportement spécialisé.
- Les adaptations ARC doivent utiliser les extensions et plugins avant toute
  modification du cœur commun.
- Les opérations destructives ou sensibles exigent une confirmation explicite
  de l’administrateur dans la conversation en cours.
- Les applications tierces suivront AACP/1 lorsqu’un connecteur sera développé.
- Le volet RAG repose sur un corpus Markdown portable, un wiki documentaire et
  une LDA calculée à partir des seules versions au statut `Applicable`.
- Les révisions documentaires suivent le cycle Brouillon, En révision, À
  approuver, Applicable, Archivé ; ARC peut proposer une révision, mais le
  workflow d'approbation contrôle sa publication.
- Le socle documentaire intégré utilise Markdown, FastAPI et React ; il reprend
  les liens et liens entrants d'Obsidian sans ajouter de service externe.
- Les clés des fournisseurs sont saisies uniquement dans Paramètres, stockées
  par le mécanisme de secrets existant et ne sont jamais renvoyées par l'API ou
  l'interface.
- Les comptes métier et jetons API sont séparés de leurs métadonnées : les
  secrets restent dans `.env`, tandis que le catalogue d’accès ne fournit à ARC
  que le service, le login, le périmètre et le nom de variable à utiliser.

## Travail en cours

- L’identité et les règles opérationnelles d’ARC sont injectées dans le prompt
  système par le plugin `arcenal-supervisor`, après la mémoire de session.
- Les tests vérifient la spécialisation et les cinq outils de supervision et
  de recherche documentaire exposés à ARC.
- Le dashboard propose les trois opérations de maintenance autorisées, impose
  une confirmation visible et transmet uniquement des identifiants bornés.
- L’API rejette les opérations inconnues, les services hors liste et les
  requêtes qui ne portent pas la confirmation administrateur.
- La livraison applicative `v0.21.0-arcenal17` et le paquet `arcenal_ynh`
  `0.21.0~ynh31` sont publiés sur GitHub. Le catalogue ARCenal direct et le
  catalogue système stable référencent la révision de paquet
  `c4c0dd83025b849e7f11e3d61875cacae1ada876`.
- Le paquet reconstruit proprement le code et les dépendances pendant
  l'upgrade, réinstalle `uv` si nécessaire et accepte la restauration
  `BACKUP_CORE_ONLY` sans masquer l'erreur initiale.
- Le build web de production exclut désormais les fichiers de test ; il réussit
  sur YunoHost sans installer `@testing-library/react`.
- Le volet ARC remplace le terminal TUI par un chat web natif relié à la
  passerelle conversationnelle Hermes. Il gère l'historique, le flux de réponse,
  l'arrêt d'une action et les validations administrateur.
- Le menu Paramètres conserve simultanément les accès OpenRouter, OpenAI,
  Anthropic, Gemini, Ollama et les clés personnalisées. Il permet de sélectionner
  le modèle principal et de choisir une autonomie manuelle, encadrée ou étendue.
- Paramètres contient désormais un coffre de comptes et d’API métier, avec une
  autonomie propre à chaque service, ainsi qu’un commutateur clair, sombre ou
  synchronisé sur le système.
- L'interface ARC reprend le thème Gratitude : fond crème et vert clair, cartes
  blanches arrondies, ombres chaudes, typographie Inter et accent terre cuite.
- Le coffre Markdown persistant, la recherche plein texte pour ARC, les liens
  entrants, l'historique, la LDA calculée et le wiki en lecture sont
  implémentés dans le plugin `arcenal-supervisor` et l'interface React.
- La LDA possède désormais son registre métier dédié avec les vues utilisables
  et archivées, les champs QSSERP, la recherche, les filtres, l'export CSV, la
  pagination, l'ouverture des fiches et l'archivage avec confirmation.
- Le formulaire de création documentaire collecte la dénomination, l'activité,
  la numérotation, la nature, la date de validation, la révision et le motif,
  tout en conservant le document source original dans un espace privé. Les
  formats PDF, DOCX, ODT, TXT et Markdown sont acceptés jusqu’à 20 Mio.
- L’historique visible depuis le chat permet maintenant d’archiver ou de
  supprimer une conversation après confirmation.
- Le wiki dispose d'une route séparée `/wiki` qui ne charge pas la façade
  d'administration et n'expose que les versions `Applicable`.
- Le paquet YunoHost fixe l'administration au groupe `admins`
  et réserve au groupe `all_users` la route du wiki et ses API de lecture.
- Le CDC approuvé est formalisé dans `docs/arcenal-product-cdc.md`.

## Validation prévue

1. Lint du projet.
2. Vérification des types applicable.
3. Tests unitaires ciblés du superviseur ARCenal.
4. Relecture du diff et contrôle de compatibilité avec le moteur amont.

Résultats du 2026-09-24 : Ruff et ESLint réussis sans erreur, vérification
TypeScript et compilation Python réussies. Pour le lot OpenRouter, 3 tests
Python isolés et 20 tests Vitest ciblés réussissent ; les tests du paquet
YunoHost et les 9 tests du catalogue réussissent également. Le build de
production Vite réussit et la page Paramètres a été contrôlée visuellement.
Le test de non-régression de l'upgrade et de sa restauration réussit. Le build
YunoHost a aussi été reproduit sans la dépendance de test absente du serveur.
Le chat ARC et le build web passent leur vérification TypeScript. Les 22 tests
Vitest ciblés, les quatre tests du paquet et les 9 tests du catalogue réussissent.
Les avertissements ESLint restants proviennent du socle Hermes préexistant. Les
tests Python du plugin n'ont pas été relancés localement faute de `pytest` dans
l'environnement disponible pour le lot précédent.
Le registre LDA passe ESLint sans nouvelle erreur, la vérification TypeScript,
13 tests Vitest ciblés, la compilation Python et le build Vite de production.
Son affichage et son formulaire de création ont été contrôlés dans le navigateur.
Le paquet ynh31 passe les six tests shell et le catalogue système ses 9 tests
Python. Les promotions development, preview et stable ainsi que la publication
GitHub Pages sont réussies ; les deux flux publics annoncent bien ynh31.
Le lot suivant passe ESLint sans erreur nouvelle, TypeScript, 27 tests Vitest,
la compilation Python, le test shell du pont YunoHost et le build Vite. Les
thèmes clair et système ainsi que le coffre d’accès ont été contrôlés dans le
navigateur. La suite Python n’a pas démarré sur le Mac faute de module `pytest`.

## Étape suivante pressentie

Actualiser le catalogue sur le serveur YunoHost de recette, installer ynh31,
puis valider le dépôt LDA, le coffre d’accès, l’historique du chat, le pont
YunoHost et les permissions réelles des espaces privés.
