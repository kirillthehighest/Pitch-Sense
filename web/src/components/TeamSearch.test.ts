import { describe, expect, it } from "vitest";
import { plain, searchTeams } from "./TeamSearch";

const team = (name: string, code = "SP1") => ({ code, league: "La Liga", season: "2026-27", team: name });
const teams = [team("Ath Madrid"), team("Barcelona"), team("Real Madrid"), team("Sociedad"), team("Man City", "E0")];

describe("finding a team", () => {
  it("ignores case and accents", () => {
    expect(plain("Atlético")).toBe("atletico");
  });

  it("finds a club by its short or its full name", () => {
    expect(searchTeams(teams, "atletico").map((found) => found.team)).toEqual(["Ath Madrid"]);
    expect(searchTeams(teams, "manchester").map((found) => found.team)).toEqual(["Man City"]);
    expect(searchTeams(teams, "bar").map((found) => found.team)).toEqual(["Barcelona"]);
  });

  it("puts the names starting with the query first", () => {
    expect(searchTeams(teams, "real").map((found) => found.team)).toEqual(["Real Madrid", "Sociedad"]);
    expect(searchTeams(teams, "madrid").map((found) => found.team)).toEqual(["Ath Madrid", "Real Madrid"]);
  });

  it("shows the first clubs when nothing is typed", () => {
    expect(searchTeams(teams, "  ", 2)).toHaveLength(2);
  });
});
