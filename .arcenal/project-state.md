# État du projet ARCenal Agent

Dernière mise à jour : 2026-09-23

Branche : `arcenal`

## Objectif courant

Transformer le fork Hermes en ARC, architecte natif d’ARCenal Système sur
YunoHost, tout en maintenant les adaptations dans une surcouche limitée afin de
faciliter les mises à jour du moteur amont.

## État observé

- Le rebranding ARCenal et le tableau de supervision sont présents.
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
- Wiki.js et BookStack sont les candidats prioritaires à comparer sur YunoHost.

## Travail en cours

- L’identité et les règles opérationnelles d’ARC sont injectées dans le prompt
  système par le plugin `arcenal-supervisor`, après la mémoire de session.
- Un test vérifie la spécialisation et le maintien des trois outils de
  supervision.
- Le dashboard propose les trois opérations de maintenance autorisées, impose
  une confirmation visible et transmet uniquement des identifiants bornés.
- L’API rejette les opérations inconnues, les services hors liste et les
  requêtes qui ne portent pas la confirmation administrateur.
- La livraison applicative `v0.21.0-arcenal9`, le paquet
  `arcenal_ynh` `0.21.0~ynh21` et sa référence dans le catalogue ARCenal sont
  publiés sur GitHub.
- La spécification fonctionnelle du RAG, de la LDA et du wiki est conservée
  dans `docs/rag-lda.md`. Son implémentation n'est pas encore commencée.

## Validation prévue

1. Lint du projet.
2. Vérification des types applicable.
3. Tests unitaires ciblés du superviseur ARCenal.
4. Relecture du diff et contrôle de compatibilité avec le moteur amont.

Résultats du 2026-09-22 : lint JavaScript/TypeScript réussi avec avertissements
préexistants, vérification TypeScript réussie, syntaxe du plugin web et
compilation Python réussies. Les scénarios directs de validation, de rejet et
d’exécution bornée passent avec le Python applicatif. Le lanceur de tests Python
ne peut pas démarrer : aucun environnement existant ne contient `pytest`.
Aucune dépendance n’a été installée sans autorisation.

Contrôle documentaire du 2026-09-23 : `git diff --check` réussit. La commande
globale `npm run check` reste inexécutable dans ce clone, car les outils locaux
`tsc` et `esbuild` ne sont pas installés. Aucun test applicatif n'est affecté
par l'ajout de la spécification RAG/LDA.

## Étape suivante pressentie

Corriger et vérifier la configuration du fournisseur OpenRouter, puis comparer
Wiki.js et BookStack sur l'instance YunoHost avant de figer l'architecture
technique du volet RAG.
