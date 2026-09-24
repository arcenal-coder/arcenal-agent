// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { ArcenalPrimaryHeader } from "@/components/ArcenalPrimaryHeader";

describe("ArcenalPrimaryHeader", () => {
  it("garde trois volets principaux et expose les paramètres séparément", () => {
    render(<MemoryRouter><ArcenalPrimaryHeader /></MemoryRouter>);

    const primary = screen.getByRole("navigation", { name: "Trois volets ARCenal" });
    expect(primary.querySelectorAll("a")).toHaveLength(3);
    expect(screen.getByRole("link", { name: "Paramètres" }).getAttribute("href")).toBe("/settings");
  });
});
