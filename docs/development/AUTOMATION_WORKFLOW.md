# Développer un workflow ARCenal

1. Déclarer un identifiant stable, un agent, un déclencheur, une version et les permissions minimales.
2. Composer uniquement des étapes prises en charge et des outils déjà autorisés à l'agent.
3. Enregistrer le workflow en `draft`.
4. Le faire passer en `testing` et vérifier le résultat nominal, la donnée absente et le refus de permission.
5. L'activer par une transition humaine authentifiée. L'identité devient `approved_by`.
6. Désactiver ou archiver dès que sa règle ou l'une de ses dépendances change.

Une étape `structured_value` sans donnée renvoie une exception contrôlée à ARC Frugal. Cette sortie est le mécanisme normal pour les cas non couverts, pas une erreur à masquer.
