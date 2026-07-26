import { cn, formatCompactNumber, formatDateLabel, formatPercent } from "@/lib/utils";

describe("utils", () => {
  it("merges class names predictably", () => {
    expect(cn("px-2", undefined, "px-4", "text-sm")).toBe("px-4 text-sm");
  });

  it("formats compact numbers for dashboard metrics", () => {
    expect(formatCompactNumber(15420.6)).toBe("15.4K");
  });

  it("formats percentages with one decimal place", () => {
    expect(formatPercent(92.44)).toBe("92.4%");
  });

  it("formats date labels for chart axes", () => {
    expect(formatDateLabel("2026-07-26T10:20:00Z")).toBe("Jul 26");
  });
});
