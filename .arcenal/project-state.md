# État du projet ARCenal Agent

Dernière mise à jour : 2026-09-24

Branche : `arcenal`

## Objectif courant

Livrer ARCenal Agent comme produit YunoHost autonome à trois volets — ARC,
Agents et RAG & LDA — sans exposer le tableau de bord Hermes comme interface
principale, tout en conservant Hermes comme moteur amont actualisable. Un accès
secondaire Paramètres permet à l'administrateur de connecter ARC à OpenRouter
sans créer un quatrième volet métier.

## État observé

- L'ancien tableau de pilotage est remplacé dans la navigation par trois
  espaces ARC, Agents et RAG & LDA ; le contrôle visuel est validé.
- Le plugin `arcenal-supervisor` expose l’état système, les rapports et trois
  réparations strictement autorisées.
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
- La clé OpenRouter est saisie uniquement dans Paramètres, stockée par le
  mécanisme de secrets existant et n'est jamais renvoyée par l'API ou l'interface.

## Travail en cours

- L’identité et les règles opérationnelles d’ARC sont injectées dans le prompt
  système par le plugin `arcenal-supervisor`, après la mémoire de session.
- Les tests vérifient la spécialisation et les cinq outils de supervision et
  de recherche documentaire exposés à ARC.
- Le dashboard propose les trois opérations de maintenance autorisées, impose
  une confirmation visible et transmet uniquement des identifiants bornés.
- L’API rejette les opérations inconnues, les services hors liste et les
  requêtes qui ne portent pas la confirmation administrateur.
- La livraison applicative `v0.21.0-arcenal12` et le paquet `arcenal_ynh`
  `0.21.0~ynh25` sont publiés sur GitHub. Le catalogue ARCenal direct référence
  cette version ; le catalogue système l'a validée et promue en `stable` à la
  révision `419a264f8ee080d4421e395ea3a5abf8d0ff07c0`.
- Le menu Paramètres permet de saisir et tester la clé OpenRouter, choisir un
  modèle puis l'activer comme modèle principal d'ARC. Le diagnostic distingue
  une clé absente, invalide ou un service OpenRouter injoignable.
- Le coffre Markdown persistant, la recherche plein texte pour ARC, les liens
  entrants, l'historique, la LDA calculée et le wiki en lecture sont
  implémentés dans le plugin `arcenal-supervisor` et l'interface React.
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
Les avertissements ESLint restants proviennent du socle Hermes préexistant.

## Étape suivante pressentie

Installer la mise à jour stable sur le serveur YunoHost de recette, puis
valider la connexion OpenRouter et les permissions réelles des espaces
d'administration et du wiki.
