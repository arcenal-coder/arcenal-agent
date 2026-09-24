import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const configuration = readFileSync(
  new URL("../../tsconfig.app.json", import.meta.url),
  "utf8",
);

describe("configuration du build de production", () => {
  it("exclut les tests TypeScript et React", () => {
    expect(configuration).toContain('"src/**/*.test.ts"');
    expect(configuration).toContain('"src/**/*.test.tsx"');
  });
});
