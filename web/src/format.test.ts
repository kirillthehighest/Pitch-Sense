import { describe, expect, it } from "vitest";
import {
  abbreviation, dateText, dayName, integer, longDateText, number, parseDay, percent, quantity,
  seasonText, shortDateText, signed, withKickoff,
} from "./format";

describe("Romanian writing, as app/services/formatting.py", () => {
  it("writes numbers with a decimal comma, a dot between thousands and a true minus", () => {
    expect(number(0.57764, 4)).toBe("0,5776");
    expect(number(-0.0073, 4)).toBe("−0,0073");
    expect(number(null)).toBe("–");
    expect(signed(0.0051, 4)).toBe("+0,0051");
    expect(signed(-0.0073, 4)).toBe("−0,0073");
    expect(percent(0.534)).toBe("53,4%");
    expect(percent(0.534, 0)).toBe("53%");
    expect(integer(28893)).toBe("28.893");
    expect(integer(380)).toBe("380");
  });

  it("writes days and seasons", () => {
    const day = parseDay("2026-10-17");
    expect(dateText(day)).toBe("17.10.2026");
    expect(shortDateText(day)).toBe("sâm. 17 oct.");
    expect(longDateText(day)).toBe("sâmbătă, 17 octombrie 2026");
    expect(longDateText(parseDay("2026-05-24"))).toBe("duminică, 24 mai 2026");
    expect(dayName(day, parseDay("2026-10-17"))).toBe("Azi");
    expect(dayName(day, parseDay("2026-10-16"))).toBe("Mâine");
    expect(dayName(day, parseDay("2026-10-18"))).toBe("Ieri");
    expect(dayName(day, parseDay("2026-10-10"))).toBe("sâm. 17 oct.");
    expect(seasonText("2006-07")).toBe("2006/07");
  });

  it("counts with the Romanian 'de'", () => {
    expect(quantity(1, "meci", "meciuri")).toBe("1 meci");
    expect(quantity(19, "meci", "meciuri")).toBe("19 meciuri");
    expect(quantity(20, "meci", "meciuri")).toBe("20 de meciuri");
    expect(quantity(101, "meci", "meciuri")).toBe("101 meciuri");
    expect(quantity(100, "meci", "meciuri")).toBe("100 de meciuri");
    expect(quantity(6080, "meci", "meciuri")).toBe("6.080 de meciuri");
  });

  it("abbreviates teams as a scoreboard does", () => {
    expect(abbreviation("Barcelona")).toBe("BAR");
    expect(abbreviation("Real Madrid")).toBe("RMA");
    expect(abbreviation("Nott'm Forest")).toBe("NFO");
  });
});

describe("the title of the featured match", () => {
  it("says whether it is the day's, the next or the last match of the league", async () => {
    const { featuredTitle } = await import("./components/FeaturedMatch");
    expect(featuredTitle("2026-10-16", "2026-10-16")).toBe("Meciul zilei");
    expect(featuredTitle("2026-10-17", "2026-10-16")).toBe("Următorul meci");
    expect(featuredTitle("2026-05-24", "2026-07-01")).toBe("Ultimul meci");
  });
});

describe("a day and its kickoff", () => {
  it("adds the kickoff, or says it is not announced yet", () => {
    expect(withKickoff("Sâm. 1 nov.", "21:00", false)).toBe("Sâm. 1 nov., 21:00");
    expect(withKickoff("Sâm. 1 nov.", null, false)).toBe("Sâm. 1 nov., ora nu e anunțată încă");
    expect(withKickoff("Sâm. 1 nov.", null, true)).toBe("Sâm. 1 nov."); // played, or postponed
  });
});
