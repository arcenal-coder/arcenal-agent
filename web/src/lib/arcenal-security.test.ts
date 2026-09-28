import { describe, expect, it } from "vitest";
import { authorizationLabel, isArcenalSecurityOverview, riskLabel } from "./arcenal-security";

const action = { allowed_targets: [], authorization: 1, consequence: "Aucune", description: "Lire", id: "system.read", risk: "none", rollback: "Aucun" };
const overview = { actions: [action], actor: { roles: ["admin"], username: "alice" }, approvals: [], audit: { events: [], integrity: true }, gateways: { control: true, readonly: true } };

describe("contrat du centre de sécurité ARCenal", () => {
  it("valide une réponse administrative complète", () => {
    expect(isArcenalSecurityOverview(overview)).toBe(true);
  });

  it("refuse une passerelle dont l’état n’est pas booléen", () => {
    expect(isArcenalSecurityOverview({ ...overview, gateways: { control: "oui", readonly: true } })).toBe(false);
  });

  it("traduit les niveaux sans exposer la représentation interne", () => {
    expect(authorizationLabel(3)).toBe("Confirmation obligatoire");
    expect(riskLabel("high")).toBe("Élevé");
  });
});
