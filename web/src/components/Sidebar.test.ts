import { describe, expect, it } from "vitest";
import { updatedText } from "./Sidebar";

describe("the side bar's note", () => {
  it("writes when the season was downloaded in the computer's time zone", () => {
    const moment = new Date(2026, 9, 15, 16, 1); // local time
    expect(updatedText(moment.toISOString())).toBe("15.10.2026, 16:01");
  });
});
