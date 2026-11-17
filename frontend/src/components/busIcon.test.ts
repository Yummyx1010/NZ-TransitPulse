import { describe, expect, it } from "vitest";

import { busIconHtml, busIconRotation, createBusIcon } from "./busIcon";

describe("bus marker icon", () => {
  it("renders an SVG bus glyph instead of a plain dot", () => {
    const html = busIconHtml();

    expect(html).toContain("<svg");
    expect(html).toContain("bus-glyph");
    expect(html).toContain("viewBox");
    expect(html).toContain("#ea580c");
    expect(html).toContain("</svg>");
  });

  it("snaps the bearing into 15-degree buckets", () => {
    expect(busIconRotation(null)).toBe(0);
    expect(busIconRotation(286)).toBe(285);
    expect(busIconRotation(360)).toBe(0);
    expect(busIconRotation(-10)).toBe(345);
    expect(busIconRotation(7)).toBe(0);
    expect(busIconRotation(8)).toBe(15);
  });

  it("reuses icons for vehicles with the same rounded heading", () => {
    const first = createBusIcon(30);
    const second = createBusIcon(32);
    const different = createBusIcon(60);

    expect(first).toBe(second);
    expect(first).not.toBe(different);
    expect(first.options.html).toContain("rotate(30deg)");
  });
});
