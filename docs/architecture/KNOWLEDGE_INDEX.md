# Index de connaissance

## Nature de l’index

`knowledge-index.json` contient la projection normalisée des documents et des
chunks. Il n’est jamais une source de vérité. La commande interne
`rebuild_index(home)` le supprime, relit les Markdown et le remplace
atomiquement.

## Déterminisme

- les fichiers sont lus dans l’ordre de leur chemin ;
- les sections suivent l’ordre du document ;
- les identifiants de chunks dérivent du document, de la version, du titre de
  section, de la position et du contenu ;
- le classement départage les scores égaux par référence, position et
  identifiant de chunk.

Une reconstruction identique conserve donc les mêmes identifiants. Les dates
de construction et de modification des sources restent naturellement
variables.

## Mise à jour

Une écriture ou une transition documentaire reconstruit immédiatement l’index.
Lorsqu’une version devient `Applicable`, le workflow archive l’ancienne version
applicable avant cette reconstruction. Les versions archivées restent dans la
projection pour une consultation historique autorisée, mais les ACL les
excluent des requêtes courantes.

Les pièces jointes TXT, Markdown, DOCX et ODT sont extraites de manière bornée
dans la fiche Markdown avant reconstruction. Les PDF utilisent le convertisseur
système `pdftotext` lorsqu’il est disponible ; son absence est signalée dans la
fiche sans supprimer la pièce jointe.

Les pages SilverBullet sont copiées dans `knowledge/.silverbullet` par une
synchronisation incrémentale fondée sur leur `ETag` ou, à défaut, leur date et
leur taille. Ce miroir est une source reconstruisible et reste en lecture seule
dans ARC. Il alimente le même index et le même filtrage ACL que les documents
locaux.
