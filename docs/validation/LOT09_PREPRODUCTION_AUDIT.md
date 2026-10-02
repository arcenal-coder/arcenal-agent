# Audit préproduction du Lot 09

Date : 2026-10-02  
Branche : `arcenal`  
Candidate cible : `v0.21.0-arcenal28`

## Objet

Cet audit vérifie la chaîne réellement utilisée par le chat ARC lorsque le
fournisseur prioritaire est indisponible. Il couvre également la propriété du
choix de modèle, qui appartient à l'agent et non au fournisseur ou au paquet
YunoHost.

## Écarts corrigés

### Contournement du runtime ARC

Le chat public créait auparavant une session directe dans la passerelle
Hermes. Le choix du fournisseur était calculé avant le message, avec une chaîne
vide, puis la requête contournait ARC Core, Agent Manager, Context Builder, le
RAG, la mémoire d'entreprise et ARC Frugal.

Le chat utilise désormais une API ARC dédiée et persistante :

```text
administrateur YunoHost
→ conversation ARC
→ ARC Core
→ Agent Manager
→ Context Builder
→ RAG et mémoire gouvernée
→ ARC Frugal
→ registre des modèles et fournisseurs
→ réponse et audit
```

Le message courant est celui transmis au classificateur et au routeur. Une
erreur fournisseur termine l'état d'attente, conserve le message utilisateur
pour diagnostic et laisse la conversation réutilisable.

### Repli Gemini

Les erreurs Gemini HTTP 503 sont classées comme indisponibilités temporaires.
En mode AUTO, ARC essaie ensuite les autres modèles autorisés, dans l'ordre du
routeur. Un test reproduit explicitement le parcours `Gemini 503 → OpenRouter`.

### Confidentialité des modèles

ARC exige un modèle autorisé pour la confidentialité du contexte traité. Le
catalogue permet maintenant à l'administrateur de déclarer le niveau maximal
de données accepté par chaque modèle. Un modèle limité aux données internes ne
peut pas recevoir silencieusement un contexte d'administration.

### Propriété du modèle

Le modèle reste défini par la politique AUTO ou FIXED de chaque agent. Le paquet
YunoHost cible ne demande plus de fournisseur, de clé ou de modèle global lors
d'une installation neuve. Les anciennes valeurs restent uniquement prises en
charge par la migration de compatibilité.

## Preuves locales

```yaml
Chat via ARC Core : PASS
Identité YunoHost propagée : PASS
Message courant transmis au routeur : PASS
RAG et mémoire dans le chemin d'exécution : PASS
Gemini 503 classé indisponible : PASS
Repli Gemini vers OpenRouter : PASS
Conversation réutilisable après erreur : PASS
Historique persistant et archivable : PASS
Permissions historique 0600 : PASS
Niveau de confidentialité des modèles modifiable : PASS
Modèle global imposé par le paquet YunoHost : SUPPRIMÉ
Secret inclus dans le registre : NON
```

## Validation automatisée

| Contrôle | Résultat |
|---|---:|
| ESLint | PASS, 0 erreur ; 28 avertissements hérités |
| Ruff ciblé | PASS |
| TypeScript Web et Dashboard | PASS |
| Compilation Python | PASS |
| Tests Python ARCenal | 217 réussis |
| Tests frontend impactés | 22 réussis |
| Build de production | PASS |
| Tests paquet YunoHost | 9 scripts et 20 tests Python réussis |
| `git diff --check` | PASS |

## Limites de preuve

La candidate n'est pas déclarée stable par cet audit local. Après publication
en `preview`, la recette réelle doit encore confirmer sur YunoHost :

- l'installation ou la mise à niveau par le catalogue ARCenal ;
- la sélection d'un modèle autorisé pour les données d'administration ;
- une réponse ARC réelle avec OpenRouter ou Codex ;
- le repli après une indisponibilité Gemini ;
- la conservation des fournisseurs, agents, secrets, RAG et mémoire après
  redémarrage du seul service ARCenal.

## Verdict

```text
READY FOR PREVIEW RECIPE
STABLE PROMOTION BLOCKED UNTIL REAL YUNOHOST PROOF
```
