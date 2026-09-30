# Sources de connaissance actuelles

Les chemins d’exécution sont relatifs à `HERMES_HOME`. Sur YunoHost, leur
emplacement physique est fixé et sauvegardé par le paquet `arcenal_ynh`.

| Source | Format et emplacement | Propriétaire / droits | Lecture / écriture | Indexation | Usage LLM actuel |
|---|---|---|---|---|---|
| Historique de chat | SQLite `state.db` | compte de service ARC | API sessions et passerelle | FTS5 | historique courant et recherche de sessions |
| Mémoire principale | Markdown `MEMORY.md` | profil concerné | gestionnaire de mémoire, API Paramètres | sections Markdown ; providers optionnels | prompt ou récupération mémoire |
| Contexte entreprise | Markdown `CONTEXT.md` | administrateur | API de fichiers gérés, versions atomiques | recherche lexicale par sections | contexte explicite |
| Directives | `AGENTS.md`, `RULES.md`, `SECURITY.md`, `TOOLS.md` | administrateur | API de fichiers gérés avec historique | aucune vectorisation | prompt système des nouvelles sessions |
| Mémoire d’un agent | `profiles/<agent>/memories/MEMORY.md` | profil spécialisé | API Agents | mécanisme mémoire du profil | agent spécialisé uniquement |
| Coffre ARC | Markdown sous `knowledge/` | administrateur documentaire | API Knowledge, écriture atomique | index central dérivé, chunks et ACL | Context Builder et outils ARC |
| Pièces jointes | `knowledge/.attachments` | service ARC | import borné et téléchargement contrôlé | aucune extraction automatique | lien vers la source, pas contenu natif |
| Historique documentaire | `knowledge/.history` | service ARC | archivage automatique, restauration confirmée | aucune | traçabilité, non injecté |
| Configuration | YAML `config.yaml` | service ARC | API de configuration validée | aucune | sélection du runtime, pas connaissance métier |
| Secrets provider | `.env` ou magasin de secrets du paquet | service ARC, mode privé | API dédiée, jamais réaffichés | aucune | authentification uniquement |
| Compétences | Markdown et ressources sous `skills/` | moteur/profil | chargeur de skills | catalogue BM25 des outils/skills | instructions chargées à la demande |
| Données d’API | HTTP/MCP/outils | application source | lecture à la demande | dépend du connecteur | résultat d’outil dans le tour courant |

## Frontières à conserver

- La LDA est une vue des documents `Applicable`, pas un stockage distinct.
- Le wiki publie uniquement cette vue autorisée.
- La mémoire de conversation, la mémoire entreprise et le corpus documentaire
  ont des cycles de vie différents et ne doivent pas être fusionnés sans
  politique de rétention et de droits.
- Les pièces jointes ne sont pas encore transformées en passages recherchables.
- Aucun vector store ARC n’est requis ; le contrat de récupération permet une
  extension sémantique ultérieure derrière les mêmes ACL.

## Découpage futur préparé

```text
LDA / Wiki        = versions documentaires approuvées
Enterprise Memory = faits et décisions durables de l’entreprise
Conversation      = messages et résumés d’une session
Process Memory    = traces structurées d’exécutions et automatisations
RAG               = index et récupération contrôlée sur ces collections
```
