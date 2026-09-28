# Décisions structurantes ARCenal Agent

## SEC-001 — Identité administrateur

- Date : 2026-09-28
- Décision utilisateur : l'administrateur ARC est un administrateur YunoHost
  existant ; aucun second mot de passe ARC n'est créé.
- Conséquence : SSOwat protège l'interface et transmet l'identité à l'API de
  contrôle. L'utilisateur choisi à l'installation reçoit aussi le rôle
  `owner`, tandis que les autres membres de `admins` gardent le rôle
  administrateur.
- Réexamen : uniquement si ARCenal Système abandonne YunoHost comme autorité
  d'identité.

## SEC-002 — Séparation des privilèges

- Date : 2026-09-28
- Décision utilisateur : aucune action privilégiée ne doit être exécutée
  directement par Hermes ou son terminal.
- Décision technique : le moteur, l'API de contrôle et le broker root utilisent
  des identités et des sockets distincts. Nginx ne possède pas l'accès au
  socket root. Le moteur ne possède qu'un socket de lecture à catalogue fermé.
- Conséquence : une réparation proposée dans le chat doit être confirmée dans
  la surface ARC authentifiée avant transmission au broker.
- Réexamen : seulement après une revue de sécurité indépendante du mécanisme de
  remplacement.

## SEC-003 — Confirmation critique

- Date : 2026-09-28
- Décision technique : une action de niveau 3 exige un identifiant imprévisible,
  créé seulement après confirmation humaine, valable cinq minutes et
  consommable une seule fois. Il est lié à l'identité, l'action et la cible,
  puis supprimé au redémarrage du service de contrôle.
- Conséquence : un booléen `confirmed=true` produit par le modèle ne constitue
  plus une autorisation.
