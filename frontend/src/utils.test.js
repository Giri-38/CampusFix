import { describe, expect, it } from "vitest";
import { countByStatus, formatDate, priorityClass, statusClass, toChartData } from "./utils.js";

describe("utils", () => {
  it("builds CSS classes", () => {
    expect(statusClass("In Progress")).toBe("s-in-progress");
    expect(statusClass("Open")).toBe("s-open");
    expect(priorityClass("High")).toBe("p-high");
  });

  it("formats dates defensively", () => {
    expect(formatDate(null)).toBe("-");
    expect(formatDate("")).toBe("-");
    expect(formatDate("not a date")).toBe("not a date");
    expect(formatDate("2026-10-31T05:40:00+00:00")).toMatch(/2026/);
  });

  it("counts complaints per status including empty ones", () => {
    const list = [{ status: "Open" }, { status: "Open" }, { status: "Resolved" }, { status: "Weird" }];
    expect(countByStatus(list, ["Open", "In Progress", "Resolved"])).toEqual({
      Open: 2,
      "In Progress": 0,
      Resolved: 1,
    });
  });

  it("converts objects to chart data", () => {
    expect(toChartData({ A: 1, B: 2 })).toEqual([
      { name: "A", value: 1 },
      { name: "B", value: 2 },
    ]);
    expect(toChartData(undefined)).toEqual([]);
  });
});
