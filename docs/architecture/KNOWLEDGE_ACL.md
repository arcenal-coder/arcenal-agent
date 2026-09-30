# ACL du RAG

## Règle de sécurité

Les ACL filtrent les documents avant la recherche et le reranking. Un fragment
interdit ne peut donc pas atteindre le prompt, même si sa correspondance
lexicale est forte.

Les contrôles sont tous cumulatifs :

- application autorisée ;
- agent autorisé ;
- utilisateur autorisé, si une liste existe ;
- permissions documentaires requises ;
- intersection des `knowledge_scopes` ;
- statut demandé par le plan ;
- type de source ;
- niveau maximal de confidentialité.

## Confidentialité

L’ordre est `public`, `internal`, `restricted`, `confidential`, `admin`.
Un agent ordinaire atteint `internal`. `knowledge.restricted` et
`knowledge.confidential` élèvent explicitement le plafond. `system.admin`
autorise le niveau `admin` pour ARC, sans modifier ses scopes.

Agent ATS conserve les scopes `ats`, `company`, `recruitment` et les seules
permissions `ats.read`, `lda.read`. Un document `accounting` restreint est
ainsi exclu avant score, même si la question le demande explicitement.
