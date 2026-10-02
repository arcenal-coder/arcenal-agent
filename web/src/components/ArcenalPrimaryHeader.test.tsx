// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { ArcenalPrimaryHeader } from "@/components/ArcenalPrimaryHeader";

describe("ArcenalPrimaryHeader", () => {
  it("place les tâches planifiées entre ARC et les agents", () => {
    render(<MemoryRouter><ArcenalPrimaryHeader /></MemoryRouter>);

    const primary = screen.getByRole("navigation", { name: "Espaces ARCenal" });
    const links = Array.from(primary.querySelectorAll("a"));
    expect(links).toHaveLength(4);
    expect(links.map((link) => link.getAttribute("href"))).toEqual([
      "/chat", "/scheduled-tasks", "/agents", "/knowledge",
    ]);
    expect(screen.getByRole("link", { name: "Paramètres" }).getAttribute("href")).toBe("/settings");
  });
});
