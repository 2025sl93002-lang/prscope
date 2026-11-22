import { describe, expect, it } from "vitest";
import { titleCase, relativeTime, formatDate } from "./format";

describe("format helpers", () => {
  it("titleCase converts kebab/snake to Title Case", () => {
    expect(titleCase("weak-copyleft")).toBe("Weak Copyleft");
    expect(titleCase("up_to_date")).toBe("Up To Date");
  });

  it("relativeTime returns 'never' for null", () => {
    expect(relativeTime(null)).toBe("never");
  });

  it("relativeTime describes a recent past time", () => {
    const tenMinAgo = Date.now() / 1000 - 600;
    expect(relativeTime(tenMinAgo)).toMatch(/minute/);
  });

  it("formatDate returns a dash for empty input", () => {
    expect(formatDate(null)).toBe("—");
    expect(formatDate(undefined)).toBe("—");
  });
});
