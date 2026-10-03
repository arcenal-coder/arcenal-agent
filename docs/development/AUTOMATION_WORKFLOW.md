# Développer un workflow ARCenal

1. Déclarer un identifiant stable, un agent, un déclencheur, une version et les permissions minimales.
2. Composer uniquement des étapes prises en charge et des outils déjà autorisés à l'agent.
3. Enregistrer le workflow en `draft`.
4. Le faire passer en `testing` et vérifier le résultat nominal, la donnée absente et le refus de permission.
5. L'activer par une transition humaine authentifiée. L'identité devient `approved_by`.
6. Désactiver ou archiver dès que sa règle ou l'une de ses dépendances change.

Une étape `structured_value` sans donnée renvoie une exception contrôlée à ARC Frugal. Cette sortie est le mécanisme normal pour les cas non couverts, pas une erreur à masquer.

## Exploitation des planifications récurrentes

- Une activation confirmée associe exactement un cron au workflow. Une nouvelle
  activation reprend ce cron tant qu'il reste récupérable.
- Une planification récurrente utilise une limite de répétition illimitée ; une
  exécution terminée ne doit donc pas désactiver le cron.
- Si un ancien cron récurrent est déjà terminal, ARC crée son remplacement en
  pause, persiste la nouvelle liaison, audite la transition, puis retire l'ancien
  cron. Un échec avant la persistance déclenche la compensation du remplacement.
- Une suspension met le cron en pause sans perdre son identifiant ni son
  historique. La réactivation ne doit créer aucun doublon.
- Pour diagnostiquer une incohérence, comparer l'état du workflow, son
  `cron_job_id`, l'entrée correspondante dans le scheduler et l'événement
  `frugal.workflow.transition` dans l'audit. Ne jamais corriger directement les
  fichiers de données sur une instance de production.
