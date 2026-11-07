import { describe, expect, it } from "vitest";
import { plain, searchPair, searchTeams } from "./TeamSearch";

const team = (name: string, code = "SP1") => ({ code, league: "La Liga", season: "2026-27", team: name });
const teams = [team("Ath Madrid"), team("Barcelona"), team("Real Madrid"), team("Sociedad"), team("Man City", "E0"), team("Man United", "E0")];

describe("finding a team", () => {
  it("ignores case and accents", () => {
    expect(plain("Atlético")).toBe("atletico");
  });

  it("finds a club by its short or its full name", () => {
    expect(searchTeams(teams, "atletico").map((found) => found.team)).toEqual(["Ath Madrid"]);
    expect(searchTeams(teams, "manchester").map((found) => found.team)).toEqual(["Man City", "Man United"]);
    expect(searchTeams(teams, "man utd").map((found) => found.team)).toEqual(["Man United"]);
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

describe("two clubs typed together", () => {
  const league = [team("Arsenal", "E0"), team("Chelsea", "E0"), team("Man City", "E0"), team("Man United", "E0")];

  it("names the home side first and the away side after", () => {
    const pair = searchPair(league, "arsenal chelsea");
    expect([pair?.home.team, pair?.away.team]).toEqual(["Arsenal", "Chelsea"]);
    const written = searchPair(league, "Man City - Man Utd");
    expect([written?.home.team, written?.away.team]).toEqual(["Man City", "Man United"]);
  });

  it("never pairs clubs of different leagues, nor finds a pair in one name", () => {
    expect(searchPair([...league, team("Barcelona")], "arsenal barcelona")).toBeNull();
    expect(searchPair(league, "arsenal")).toBeNull();
  });
});
