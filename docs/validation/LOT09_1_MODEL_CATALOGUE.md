# Lot 09.1 — Catalogue de modèles et politiques par agent

Date de validation locale : 2026-10-02  
Branche : `arcenal`  
Candidate : `v0.21.0-arcenal24` / `0.21.0~ynh42`

## Cause

Le Model Registry et ARC Frugal existaient, mais trois liaisons avaient été
perdues dans l'interface applicative : le catalogue n'était plus présenté comme
source de vérité, le gestionnaire d'agents ne persistait pas une politique
AUTO ou FIXED complète, et le test d'un fournisseur ne synchronisait pas les
modèles découverts vers le registre existant.

La bulle utilisateur utilisait bien la couleur dominante. Le composant Markdown
réappliquait toutefois ses couleurs génériques `foreground` et `primary`, ce qui
écrasait la couleur héritée de la bulle. La correction relie désormais le fond
et toutes les couleurs Markdown aux tokens sémantiques `--arc-primary` et
`--arc-primary-text`. Ce dernier est calculé par le mécanisme de contraste de
l'apparence, y compris pour une couleur dominante claire.

## Model Registry

```text
providers : 9 familles ARC déclarées ; registre persistant unique
modèles : configurés, statiques ou découverts ; aucune liste distante inventée
discovery dynamique : Gemini, OpenRouter et endpoints compatibles existants
catalogue statique : conservé avec la source explicite configured/static
```

Gemini ne conserve que les modèles annonçant `generateContent`. Une découverte
réussie ajoute ou actualise les modèles dans le registre et marque indisponibles
les entrées découvertes qui ont disparu, sans supprimer leur historique.

## Agents

```text
AUTO : PASS
FIXED : PASS
modification : PASS
local_preferred : PASS
local_only : PASS
modèle absent/désactivé : refusé
pseudo-modèle auto en FIXED : refusé
```

Le mode FIXED stocke l'identifiant du registre, puis le routeur transmet le nom
concret au Provider Adapter. Les chemins déterministe, cache et workflow restent
évalués avant tout appel LLM.

## Gemini et chat

```text
authentification : PASS — preuve réelle antérieure, HTTP 429 atteint Google
modèle concret : PASS — contrat et routage validés localement
quota : LIMITÉ
429 proprement traité : PASS
état analyse correctement terminé sur erreur : PASS
réponse réelle avec provider disponible : NON TESTÉ
```

Le message de quota ne contient aucune affirmation commerciale variable. Les
valeurs ressemblant à une clé, un jeton, un mot de passe ou un Bearer sont
expurgées des autres erreurs avant affichage.

## Interface et accessibilité

```yaml
Catalogue modèles visible : PASS
Modèle AUTO par agent : PASS
Modèle FIXED par agent : PASS
Modification du modèle d'un agent : PASS
Gemini 429 correctement traité : PASS
Chat débloqué après erreur provider : PASS
Bulle utilisateur — contraste : PASS
Bulle utilisateur — thème clair : PASS
Bulle utilisateur — thème sombre : PASS
Markdown dans bulle utilisateur : PASS
```

Les preuves automatisées vérifient le token de fond, le token de contraste, les
couleurs Markdown et le calcul clair/sombre pour une dominante claire ou sombre.
La recette installée devra encore confirmer visuellement le message « Analyse
l'état du serveur » après mise à niveau depuis le canal preview.

## RAG

```text
PASS — 10 tests RAG et la suite ARCenal complète restent verts
```

## Contrôles exécutés

| Contrôle | Résultat |
|---|---:|
| Ruff ciblé | PASS |
| ESLint | PASS, 0 erreur ; 28 avertissements hérités |
| `ty` ciblé | PASS |
| Compilation Python | PASS |
| TypeScript Web et Dashboard | PASS |
| Tests impactés Python | 50 réussis |
| Tests impactés frontend | 40 réussis, puis 4 tests de rendu catalogue |
| Non-régression Python ARCenal | 237 réussis |
| Non-régression frontend | 437 réussis, 65 fichiers |
| Scénarios shell YunoHost | 9 réussis |
| Broker et attente socket | 20 réussis |
| Catalogue ARCenal | 13 réussis |
| Build de production | PASS |
| `git diff --check` | PASS |

## Complexité

```text
fichiers ajoutés : 1 rapport de validation
fichiers de code, test ou configuration modifiés : 26
dépendances ajoutées : 0
services ajoutés : 0
bases ajoutées : 0
```

## Candidate

```text
Application : v0.21.0-arcenal24
Package YunoHost : 0.21.0~ynh42
Révisions applicatives : 7589b5211c, a1f0443cfa, 7b6572d404
Canal preview : uniquement
Canal stable : inchangé
```

## Verdict

```text
READY FOR FINAL LOT 09R RECIPE
```
