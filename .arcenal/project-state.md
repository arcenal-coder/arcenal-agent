# État du projet ARCenal Agent

Dernière mise à jour : 2026-09-22

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

## Travail en cours

- L’identité et les règles opérationnelles d’ARC sont injectées dans le prompt
  système par le plugin `arcenal-supervisor`, après la mémoire de session.
- Un test vérifie la spécialisation et le maintien des trois outils de
  supervision.

## Validation prévue

1. Lint du projet.
2. Vérification des types applicable.
3. Tests unitaires ciblés du superviseur ARCenal.
4. Relecture du diff et contrôle de compatibilité avec le moteur amont.

Résultats du 2026-09-22 : lint JavaScript/TypeScript réussi avec avertissements
préexistants, vérification TypeScript réussie, compilation Python réussie. Le
lanceur de tests Python ne peut pas démarrer : aucun environnement existant ne
contient `pytest`. Aucune dépendance n’a été installée sans autorisation.

## Étape suivante pressentie

Ajouter au tableau de supervision le cycle maintenance sécurisé : proposition,
confirmation administrateur, exécution bornée et compte rendu vérifiable.
