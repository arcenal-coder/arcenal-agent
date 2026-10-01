# Audit des dépendances

Date : 2026-10-01. Le paquet exécute actuellement `uv sync --no-dev` sur le
projet Hermes/ARCenal puis construit les workspaces web et TUI. Aucun module
supplémentaire n’a été installé pendant cet audit.

## Classement

| Classe | Dépendances ou groupes | Usage actuel | Décision |
|---|---|---|---|
| ESSENTIAL | Python, FastAPI, serveur ASGI, Pydantic | API, validation stricte, dashboard | conserver |
| USEFUL | PyYAML/ruamel.yaml, dotenv | configuration générale HERMES | conserver pour l’amont, ARC natif utilise la bibliothèque standard |
| ESSENTIAL | client HTTP, OpenAI-compatible, certificats | fournisseurs distants et SilverBullet | conserver derrière les adapters |
| ESSENTIAL | frontend React/Vite et build ARC | interface à trois volets | conserver |
| ESSENTIAL | SQLite standard | registres, mémoire, audit et cache | conserver |
| USEFUL | `psutil` | métriques et diagnostic | conserver, mesurer son usage |
| USEFUL | `websockets` | événements de chat | conserver tant que le dashboard l’utilise |
| USEFUL | `python-multipart` | dépôt de documents LDA | conserver |
| USEFUL | `ripgrep`, `curl`, `git`, `ffmpeg` | outils et fonctions historiques | réévaluer par capacité ARC activée |
| LEGACY | CLI/TUI et passerelles Hermes non activées sur YunoHost | héritage du runtime amont | isoler, ne pas étendre |
| LEGACY | compétences Hermes copiées au premier démarrage | catalogue historique | filtrer dans un futur profil ARC minimal |
| CANDIDATE_FOR_REMOVAL | dépendances voix, médias et intégrations non utilisées par ARC | héritage amont ou extras | prouver l’absence d’usage avant retrait |
| CANDIDATE_FOR_REMOVAL | affichage de version et libellés Hermes | diagnostic historique | retirer après versionnage runtime ARC |
| CANDIDATE_FOR_REMOVAL | dépendances de build conservées après compilation | installation npm actuelle | vérifier que TUI et web sont autonomes avant nettoyage |

## Mesure du périmètre actuel

- Environnement Python local : 98 distributions installées, 271 Mio.
- Build web produit : 3,8 Mio.
- Plugin ARCenal : 1,2 Mio.
- Le projet déclare beaucoup de capacités Hermes générales ; toutes ne sont pas
  nécessaires au rôle YunoHost d’ARC.

Ces chiffres démontrent une marge de simplification, pas une liste de modules à
supprimer immédiatement. Le retrait devra partir des imports et parcours réels,
avec un test d’installation et un test fonctionnel après chaque capacité
extraite.

## Risques de packaging

1. `uv` est téléchargé par son installateur officiel avec une version épinglée,
   mais hors de la ressource `sources` vérifiée par SHA-256.
2. Le build installe les dépendances npm de la racine, du web et du TUI. Leur
   présence après compilation peut augmenter la taille installée.
3. Le paquet APT inclut `ffmpeg` alors qu’aucun parcours ARC obligatoire ne le
   requiert actuellement.
4. Les dépendances racine mélangent runtime serveur, outils personnels et
   intégrations optionnelles héritées.

## Direction de simplification

- Ne pas supprimer au hasard dans le paquet actuel.
- Définir un groupe de dépendances `arc-runtime` à partir d’imports prouvés.
- Garder un adaptateur Hermes installable pendant la transition.
- Mesurer taille, démarrage, RAM et tests après chaque extraction.
- Refuser Redis, PostgreSQL, Kubernetes, broker de messages ou base vectorielle
  externe sans besoin démontré.

## Effet du Lot 08

Le stockage natif de configuration et le coffre ARC utilisent uniquement la
bibliothèque standard Python. Aucun paquet, service système ou processus
résident supplémentaire n’a été ajouté. L’extraction réduit les imports directs
de configuration HERMES de sept à un, sans retirer les dépendances encore
utilisées par le runtime amont.

## Effet du Lot 09

ARC Config et ARC Vault deviennent nominaux sans ajouter de paquet Python, de
service ou de base. Le dernier import HERMES Config est tardif et réservé à la
migration. L’API native réutilise FastAPI et Pydantic déjà présents. Le paquet
YunoHost exécute une commande Python courte pendant install, upgrade ou restore
et conserve `config.yaml` intact pour réversibilité.
