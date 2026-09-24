# Cahier des charges — ARCenal Agent

Version : **1.0 approuvée**

Date : 24 septembre 2026

## Positionnement

ARCenal Agent est l'application native d'administration intelligente
d'ARCenal Système sur YunoHost. Son agent principal se nomme **ARC**. Hermes
Agent reste le moteur technique amont et n'apparaît que sous la mention
discrète « by Hermes ».

La surcouche ARCenal doit rester limitée et périphérique afin que les versions
amont puissent être intégrées rapidement.

## Accès et sécurité

- installation et mise à jour exclusivement par le paquet YunoHost ;
- accès à l'administration limité au groupe YunoHost `admins` ;
- secrets conservés dans les données privées de l'application ;
- opérations sensibles soumises à confirmation explicite ;
- aucune commande libre construite depuis une entrée utilisateur privilégiée.

## Interface principale

La navigation principale comporte exactement trois volets.

### 1. ARC

Chat permettant de diagnostiquer, expliquer, superviser, maintenir et
configurer le serveur et ses applications. ARC utilise les observations
réelles du système, cite les faits mesurés et vérifie les actions exécutées.

### 2. Agents

Création d'agents spécialisés avec identité, mission, fournisseur, modèle,
compétences et mémoire isolés. Les connecteurs applicatifs ne sont pas activés
dans cette version ; leur futur contrat de sécurité est AACP/1.

### 3. RAG & LDA

Coffre documentaire open source inspiré du parcours Obsidian :

- fichiers Markdown portables avec métadonnées ;
- arborescence, recherche plein texte, liens `[[Wiki]]`, tags et aperçu ;
- édition et conservation dans le répertoire de données ARC ;
- recherche RAG par ARC avec référence, version et statut des sources ;
- LDA calculée à partir des seules versions `Applicable` ;
- vue wiki issue de cette même publication ;
- export CSV de la LDA.

Le cycle documentaire est : Brouillon, En révision, À approuver, Applicable,
Archivé. ARC peut préparer une révision, mais ne peut pas publier seul une
version applicable.

## Critères d'acceptation

1. L'arrivée dans l'application ouvre ARC et non un écran de pilotage Hermes.
2. Les seuls volets principaux visibles sont ARC, Agents et RAG & LDA.
3. Un agent spécialisé peut être créé et persiste comme profil isolé.
4. Un document Markdown peut être créé, lu, modifié et recherché.
5. Un document applicable apparaît automatiquement dans la LDA et le wiki.
6. Un brouillon, une révision ou une archive n'apparaît pas dans ces vues.
7. ARC peut rechercher un document et restituer une source traçable.
8. Le paquet YunoHost conserve les données lors d'une mise à jour.
