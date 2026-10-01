# Directive visuelle — Thème Gratitude amélioré

Statut : directive de référence
Version : 1.0
Périmètre : interfaces ARCenal destinées aux utilisateurs et aux administrateurs
Référence d’origine : identité visuelle de l’application Gratitude

## 1. Intention

Le thème Gratitude amélioré doit donner aux produits ARCenal une identité
chaleureuse, calme et professionnelle. L’interface doit inspirer confiance sans
ressembler à un tableau de bord technique générique, à un terminal ou à un
logiciel froid d’administration système.

Le thème repose sur cinq principes :

1. **Clarté immédiate** : l’action principale et l’état du système sont compris
   sans apprentissage.
2. **Sérénité** : les couleurs, les espaces et les mouvements réduisent la
   charge cognitive.
3. **Sobriété B2B** : le rendu reste crédible pour un usage professionnel,
   documentaire et réglementaire.
4. **Chaleur maîtrisée** : la terre cuite apporte la personnalité ; elle ne doit
   jamais envahir tout l’écran.
5. **Accessibilité** : la lisibilité, le clavier et les contrastes priment sur
   les effets décoratifs.

## 2. Règles structurantes

- Utiliser une composition lumineuse, aérée et organisée par cartes.
- Employer la terre cuite pour les actions principales, la sélection et les
  repères de marque.
- Réserver le vert aux états positifs, disponibles ou conformes.
- Utiliser l’or avec parcimonie pour les avertissements non bloquants.
- Utiliser le rouge sombre uniquement pour les erreurs et actions destructives.
- Ne jamais coder directement une couleur dans un composant : utiliser les
  variables sémantiques `--arc-*`.
- Conserver une seule action principale visuellement dominante par zone.
- Préférer une hiérarchie en trois niveaux maximum : page, section, composant.
- Employer des libellés métier compréhensibles et masquer le vocabulaire
  technique qui n’aide pas l’utilisateur.
- Afficher « by Hermes » uniquement comme une mention discrète de filiation
  technique, jamais comme une marque principale.

## 3. Palette de référence

### 3.1 Mode clair

| Rôle | Variable | Valeur | Usage |
|---|---|---:|---|
| Fond principal | `--arc-background` | `#FFF9EF` | Toile générale chaude |
| Fond secondaire | `--arc-background-tint` | `#F3FAF4` | Extrémité du dégradé, zones calmes |
| Surface principale | `--arc-surface` | `#FFFDF8` | Cartes, dialogues, navigation |
| Surface secondaire | `--arc-surface-secondary` | `#FFF7E8` | Encadrés, champs inactifs, groupes |
| Texte principal | `--arc-text` | `#1F2937` | Titres et contenu |
| Texte secondaire | `--arc-text-secondary` | `#64748B` | Aides, métadonnées, légendes |
| Bordure | `--arc-border` | `#E9E3D7` | Séparation douce |
| Champ | `--arc-input` | `#D7D1C5` | Bordure des saisies |
| Action principale | `--arc-primary` | `#D45D36` | Boutons, sélection, repères |
| Action survolée | `--arc-primary-hover` | `#B84B2C` | Survol et pression |
| Texte sur action | `--arc-primary-text` | `#FFFFFF` | Texte et icône sur terre cuite |
| Succès | `--arc-success` | `#26705D` | Disponible, validé, conforme |
| Avertissement | `--arc-warning` | `#B7791F` | Attention, validation requise |
| Erreur | `--arc-error` | `#9D3D25` | Échec, danger, suppression |
| Focus | `--arc-focus` | `#3157A4` | Anneau clavier accessible |

Le fond général utilise un dégradé très léger :

```css
background: linear-gradient(135deg, #fff9ef 0%, #f3faf4 100%);
```

Ce dégradé appartient à la toile de fond. Il ne doit pas être répété sur toutes
les cartes ou tous les boutons.

### 3.2 Mode sombre

Le mode sombre conserve la chaleur du thème. Il ne doit pas devenir noir pur ni
transformer l’interface en terminal.

| Rôle | Variable | Valeur |
|---|---|---:|
| Fond principal | `--arc-background` | `#17191E` |
| Fond secondaire | `--arc-background-tint` | `#1C2421` |
| Surface principale | `--arc-surface` | `#20232A` |
| Surface secondaire | `--arc-surface-secondary` | `#292C33` |
| Texte principal | `--arc-text` | `#F5F0E8` |
| Texte secondaire | `--arc-text-secondary` | `#B8B1A7` |
| Bordure | `--arc-border` | `#3A3D45` |
| Champ | `--arc-input` | `#4A4D55` |
| Action principale | `--arc-primary` | `#E47A55` |
| Action survolée | `--arc-primary-hover` | `#F08A65` |
| Texte sur action | `--arc-primary-text` | `#17191E` |
| Succès | `--arc-success` | `#5AAE91` |
| Avertissement | `--arc-warning` | `#E9B85D` |
| Erreur | `--arc-error` | `#EF8069` |
| Focus | `--arc-focus` | `#8FB4FF` |

### 3.3 Mode système

Le choix « Système » suit `prefers-color-scheme` en temps réel. Un choix manuel
« Clair » ou « Sombre » reste prioritaire et persiste pour l’utilisateur.

## 4. Contrat des variables CSS

Toute interface ARCenal doit consommer au minimum le contrat suivant :

```css
--arc-background
--arc-background-tint
--arc-surface
--arc-surface-secondary
--arc-text
--arc-text-secondary
--arc-border
--arc-input
--arc-primary
--arc-primary-hover
--arc-primary-text
--arc-success
--arc-warning
--arc-error
--arc-focus
--arc-shadow-card
--arc-shadow-hover
--arc-font-ui
--arc-font-display
```

Les couleurs propres à un métier peuvent être ajoutées, mais elles doivent être
mappées vers un rôle sémantique. Un composant ne doit pas dépendre d’un nom de
couleur comme `orange`, `green` ou `blue`.

## 5. Typographie

- Police d’interface : `Inter`, puis les polices système sans serif.
- Police de titre : la police d’interface par défaut. Une police éditoriale peut
  être utilisée uniquement pour les grands titres de présentation si elle est
  déjà fournie par le produit.
- Corps courant : `16px`, interligne de `1.5`.
- Corps compact : `14px`, réservé aux tableaux et métadonnées.
- Taille minimale visible : `12px`. Aucun texte fonctionnel ne doit être plus
  petit.
- Titre de page : de `32px` à `44px`, graisse `700` ou `800`.
- Titre de section : de `20px` à `26px`, graisse `650` à `750`.
- Libellé : `14px`, graisse `600`.
- Les textes entièrement en majuscules sont réservés aux petits repères de
  section et doivent conserver un espacement de lettres modéré.

Les titres doivent être courts. Les paragraphes longs restent alignés à gauche
et leur largeur ne dépasse pas environ 75 caractères.

## 6. Grille, dimensions et rythme

- Grille d’espacement : multiples de `4px`, avec un rythme principal de `8px`.
- Largeur utile recommandée : `1180px` à `1280px`.
- Marge extérieure sur grand écran : `24px` minimum.
- Marge extérieure sur mobile : `16px`.
- Espace entre grandes sections : `32px` à `48px`.
- Espace interne d’une carte : `20px` à `28px`.
- Hauteur minimale d’une cible tactile : `44px`.
- Rayon d’une carte : `16px` à `18px`.
- Rayon d’un bouton ou d’un champ : `10px` à `12px`.
- Les pastilles d’état peuvent utiliser un rayon complet.

Le vide est un élément du thème. Il sert à séparer les responsabilités et ne
doit pas être comblé par des widgets secondaires.

## 7. Élévation et profondeur

Les ombres sont chaudes, diffuses et peu nombreuses :

```css
--arc-shadow-card: 0 14px 38px rgb(69 48 29 / 10%);
--arc-shadow-hover: 0 20px 46px rgb(69 48 29 / 16%);
```

- Une carte au repos utilise au plus l’ombre de carte.
- Une carte interactive peut utiliser l’ombre de survol.
- Les bordures restent visibles même avec une ombre.
- Les ombres noires dures, l’effet néon et le verre excessivement transparent
  sont interdits.

## 8. Composants

### 8.1 En-tête et navigation

- Afficher le logo de l’organisation configuré dans YunoHost ; utiliser le logo
  ARCenal comme solution de secours.
- Limiter la navigation principale aux espaces métier réellement disponibles.
- Montrer clairement l’espace actif avec un fond terre cuite ou une bordure
  forte, sans multiplier les indicateurs.
- Sur mobile, transformer la navigation en barre compacte ou en menu contrôlé.
- Ne jamais afficher la navigation technique héritée de Hermes dans la façade
  principale ARCenal.

### 8.2 Cartes

- Fond ivoire, bordure douce, rayon généreux et ombre chaude.
- Un titre, une intention et une action principale au maximum dans l’en-tête.
- Les cartes de statut associent une icône, un libellé et une valeur ; la
  couleur seule ne suffit pas.
- Les cartes cliquables réagissent au survol, au focus et à l’activation.

### 8.3 Boutons

- Primaire : fond terre cuite, texte contrasté.
- Secondaire : surface claire, bordure, texte principal.
- Tertiaire : texte ou icône, sans masse visuelle inutile.
- Destructif : rouge sombre, confirmation explicite pour toute perte de donnée.
- Une icône seule possède toujours un libellé accessible et une infobulle.
- Les états chargement, désactivé, succès et erreur sont visibles.

### 8.4 Champs et formulaires

- Placer le libellé au-dessus du champ.
- Afficher l’aide avant l’erreur et l’erreur directement sous le champ.
- Ne jamais utiliser le texte indicatif comme unique libellé.
- Regrouper les champs par intention métier, pas par structure technique.
- Les secrets peuvent être révélés temporairement, mais ne sont jamais
  réaffichés après enregistrement.

### 8.5 Tableaux et LDA

- Conserver l’en-tête visible dans les longues listes.
- Utiliser des lignes aérées, des séparateurs fins et des badges sobres.
- Donner la priorité au titre du document, à son statut, à sa version et à sa
  date d’application.
- Sur petit écran, passer en cartes ou autoriser un défilement horizontal
  explicitement signalé.
- Recherche, filtres, tri, export et pagination restent regroupés dans une
  barre d’outils unique.
- Les actions d’archivage et de suppression sont distinctes et confirmées.

### 8.6 Chat ARC

- Présenter une conversation humaine, pas une sortie de terminal.
- Différencier clairement les messages de l’utilisateur, d’ARC et du système.
- Garder la zone de saisie visible et suffisamment haute pour une consigne.
- Montrer les étapes d’une opération longue en langage naturel.
- Afficher les demandes de confirmation dans une carte dédiée, avec le risque,
  la cible et les conséquences.
- Permettre de créer, renommer, archiver et supprimer une conversation.
- Les traces techniques détaillées restent dans les journaux, pas dans le fil
  principal.

### 8.7 RAG, wiki et graphe documentaire

- Séparer visuellement le coffre documentaire, la LDA, le wiki publié et le
  graphe de connaissances.
- Représenter les liens du graphe par des traits droits ou légèrement brisés,
  jamais par un réseau organique décoratif.
- Afficher la source, la version, le statut et les droits avec chaque résultat.
- Une citation doit ouvrir le document et l’extrait ayant justifié la réponse.
- Le wiki salarié reste plus simple que l’interface d’administration.

## 9. États et retours utilisateur

Chaque écran de données doit prévoir :

- un chargement explicite sans saut brutal de mise en page ;
- un état vide qui explique l’usage et propose la première action ;
- un état d’erreur compréhensible avec une possibilité de reprise ;
- un état sans résultat distinct d’une erreur ;
- une confirmation visible après enregistrement ;
- un avertissement avant une action irréversible.

Les messages techniques du fournisseur, du moteur ou de YunoHost sont traduits
en une formulation utile. Le détail brut peut être proposé dans une zone
secondaire pour le diagnostic administrateur.

## 10. Mouvement

- Durée standard : `160ms` à `220ms`.
- Courbe : accélération douce, sans rebond décoratif.
- Animer uniquement les changements qui aident à comprendre la relation entre
  deux états.
- Respecter `prefers-reduced-motion` et supprimer alors les déplacements non
  indispensables.
- Interdire les animations permanentes hors indicateur d’activité réel.

## 11. Accessibilité obligatoire

- Respecter au minimum WCAG 2.2 niveau AA.
- Contraste du texte courant : `4.5:1` minimum.
- Contraste du grand texte et des éléments graphiques essentiels : `3:1`
  minimum.
- Focus clavier visible avec un anneau d’au moins `2px`.
- Parcours complet au clavier, ordre de tabulation cohérent et échappement des
  dialogues avec la touche Échap.
- Aucun état communiqué uniquement par la couleur.
- Icônes décoratives masquées aux technologies d’assistance ; icônes d’action
  nommées.
- Zoom à `200 %` sans perte de fonction ni chevauchement bloquant.
- Zones tactiles de `44 × 44px` recommandées.

## 12. Responsive

Trois comportements sont attendus, sans imposer des appareils précis :

- **Large** : plusieurs colonnes, panneau contextuel possible.
- **Intermédiaire** : réduction des colonnes et déplacement des panneaux
  secondaires sous le contenu principal.
- **Compact** : une seule colonne, navigation condensée, actions principales
  persistantes si nécessaire.

Le contenu décide du point de rupture. Une interface ne doit jamais réduire les
textes sous la taille minimale pour tenir dans la largeur.

## 13. Personnalisation de l’organisation

Le thème accepte la personnalisation sans perdre sa cohérence :

- logo, nom, favicon et couleur d’accent proviennent d’abord de la configuration
  ARCenal ;
- la personnalisation publique YunoHost sert de valeur de secours ;
- le logo ARCenal est le dernier secours ;
- une couleur personnalisée doit conserver un contraste conforme ; sinon
  l’interface calcule ou choisit une variante accessible ;
- la couleur d’accent ne remplace pas les couleurs sémantiques de succès,
  d’avertissement et d’erreur.

## 14. Interdictions

- Pas de terminal Hermes comme interface principale.
- Pas de barre latérale technique héritée du moteur.
- Pas de multiplication de couleurs d’accent concurrentes.
- Pas de texte fonctionnel inférieur à `12px`.
- Pas de contraste gris clair sur fond blanc pour une information importante.
- Pas de carte dans une carte dans une carte.
- Pas de dégradé décoratif sur chaque composant.
- Pas de boutons uniquement reconnaissables par leur couleur.
- Pas de jargon technique si une formulation métier existe.
- Pas d’opération destructive sans confirmation et description de l’impact.
- Pas de faux état fonctionnel : une action visible doit être réellement
  utilisable ou clairement signalée comme indisponible.

## 15. Priorité d’application

Cette directive s’applique aux nouvelles interfaces ARCenal et aux écrans
existants lorsqu’ils sont modifiés. Elle ne justifie pas à elle seule une
réécriture globale du moteur Hermes.

L’ordre de priorité est le suivant :

1. accessibilité et sécurité ;
2. cohérence métier et compréhension ;
3. contrat sémantique du thème ;
4. composition et responsive ;
5. décoration et mouvement.

Les adaptations doivent rester dans la façade, les extensions et les plugins
ARCenal autant que possible afin de préserver la capacité de mise à jour du
socle Hermes.

## 16. Critères de validation

Une interface conforme doit répondre « oui » à chaque point :

- [ ] Le mode clair, le mode sombre et le mode système fonctionnent.
- [ ] Les couleurs proviennent des variables sémantiques `--arc-*`.
- [ ] Le logo et le nom de l’organisation utilisent la chaîne de secours prévue.
- [ ] L’action principale est identifiable en moins de trois secondes.
- [ ] Tous les textes fonctionnels mesurent au moins `12px`.
- [ ] Le clavier permet d’utiliser tout le parcours.
- [ ] Le focus est toujours visible.
- [ ] Les contrastes respectent WCAG AA.
- [ ] Les états chargement, vide, erreur et succès sont prévus.
- [ ] Les actions sensibles affichent leur impact et demandent confirmation.
- [ ] La mise en page reste utilisable sur écran compact et à zoom `200 %`.
- [ ] Aucun élément technique Hermes ne concurrence l’identité ARCenal.
- [ ] Les composants réutilisent le socle commun plutôt que des styles locaux.
- [ ] Les tests visuels couvrent les deux modes, les trois largeurs et les états
      critiques.

## 17. Consigne opérationnelle pour les futurs développements

> Concevoir l’interface selon le thème Gratitude amélioré : fond chaud crème et
> vert très pâle, surfaces ivoire, cartes arrondies, ombres chaudes discrètes,
> typographie Inter lisible et accent terre cuite limité aux actions et repères
> importants. Préserver une apparence B2B calme, claire et accessible. Utiliser
> exclusivement les variables sémantiques `--arc-*`, prévoir clair, sombre et
> système, tous les états fonctionnels, le clavier, le responsive et les
> contrastes WCAG AA. Conserver ARCenal comme identité publique et Hermes comme
> moteur discret. Ne jamais reproduire une interface de terminal ou la
> navigation technique Hermes dans la façade utilisateur.
