import { describe, expect, it } from "vitest";
import { accessCredentialsFromConfig, createAccessCredential } from "./arcenal-access";

describe("gestion des accès ARC", () => {
  it("prépare un compte avec un secret serveur dédié", () => {
    const credential = createAccessCredential({ autonomy: "smart", kind: "account", label: "Portail RH", login: "arc.admin", secret: "secret", serviceUrl: "https://rh.example.test" }, []);
    expect(credential).toMatchObject({ id: "portail_rh", login: "arc.admin", secretEnv: "ARCENAL_ACCESS_PORTAIL_RH_PASSWORD" });
  });

  it("rend les identifiants uniques sans exposer le secret", () => {
    const first = createAccessCredential({ autonomy: "manual", kind: "api", label: "QSS ERP", login: "", secret: "token", serviceUrl: "https://qss.example.test" }, []);
    const second = createAccessCredential({ autonomy: "off", kind: "api", label: "QSS ERP", login: "", secret: "other", serviceUrl: "https://qss.example.test" }, [first]);
    expect(second.id).toBe("qss_erp_2");
    expect(second).not.toHaveProperty("secret");
  });

  it("rejette un compte incomplet ou une adresse dangereuse", () => {
    expect(() => createAccessCredential({ autonomy: "manual", kind: "account", label: "NAS", login: "", secret: "secret", serviceUrl: "https://nas.test" }, [])).toThrow("login");
    expect(() => createAccessCredential({ autonomy: "manual", kind: "api", label: "Local", login: "", secret: "token", serviceUrl: "file:///etc/passwd" }, [])).toThrow("HTTP");
  });

  it("ignore les entrées de configuration invalides", () => {
    const config = { arcenal: { access_credentials: [{ id: "ok", kind: "api", label: "API", secretEnv: "ARCENAL_ACCESS_OK_API_KEY", serviceUrl: "https://api.test", autonomy: "smart" }, { id: "bad", kind: "api", label: "Dangereux", secretEnv: "PATH", serviceUrl: "https://api.test", autonomy: "off" }] } };
    expect(accessCredentialsFromConfig(config)).toHaveLength(1);
  });
});
