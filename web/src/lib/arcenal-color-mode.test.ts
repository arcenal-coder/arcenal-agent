import { describe, expect, it } from "vitest";
import { resolveColorMode } from "./arcenal-color-mode";

describe("apparence ARCenal", () => {
  it("respecte le choix sombre", () => expect(resolveColorMode("dark", false)).toBe("dark"));
  it("respecte le choix clair", () => expect(resolveColorMode("light", true)).toBe("light"));
  it("suit le système", () => {
    expect(resolveColorMode("system", true)).toBe("dark");
    expect(resolveColorMode("system", false)).toBe("light");
  });
});
