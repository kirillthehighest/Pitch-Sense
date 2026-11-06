// The chosen league's match of the day at the top of the matches screen, as the hero cards of the
// references (when the league does not play that day, its next match, else its last one):
// the league's image, both teams with their crests in large capitals (and the score once played),
// the day and kickoff, the chosen model's three probabilities and a button to the match's page.
// The card shows the match's league image; its colours are PitchSense's (Phase 26).
import { capitalised, parseDay, percent, shortDateText, teamName, withKickoff } from "../format";
import { IMAGE_FILL } from "../theme";
import type { Forecast, League, Outcome } from "../types";
import { MODEL_LABELS } from "../types";
import { Crest } from "./Crest";
import { LeagueImageCard } from "./LeagueImage";
import { chance } from "./MatchRow";

const OUTCOMES: [Outcome, string][] = [["H", "Gazde"], ["D", "Egal"], ["A", "Oaspeți"]];

/** What the card is: the match of the day shown, or the league's next or last one. */
export function featuredTitle(matchDay: string, shownDay: string): string {
  if (matchDay === shownDay) return "Meciul zilei";
  return matchDay > shownDay ? "Următorul meci" : "Ultimul meci";
}

interface Props {
  forecast: Forecast;
  day: string; // the day on screen
  league: League;
  model: string;
  favourite: string | null;
  onOpen: (forecast: Forecast) => void;
}

export function FeaturedMatch({ forecast, day, league, model, favourite, onOpen }: Props) {
  const prediction = forecast.predictions.find((p) => p.model === model);
  const played = forecast.result !== null;
  const when = withKickoff(capitalised(shortDateText(parseDay(forecast.date))), forecast.kickoff, played || forecast.postponed);
  const teams: [string, number | null][] = [
    [forecast.home_team, forecast.home_goals],
    [forecast.away_team, forecast.away_goals],
  ];
  return (
    <LeagueImageCard
      code={league.code}
      top={league.photo_top}
      credit={league.photo_credit}
      brand={IMAGE_FILL}
      className="featured"
    >
      <span className="eyebrow">
        {featuredTitle(forecast.date, day)} · {league.name}
      </span>
      <div className="featured-teams">
        {teams.map(([team, goals]) => (
          <div key={team} className="featured-team">
            <Crest team={team} size={40} ring={team === favourite} />
            <span>{teamName(team)}</span>
            {goals !== null && <strong>{goals}</strong>}
          </div>
        ))}
      </div>
      <span className="featured-info">
        {played ? `Final · ${when}` : when} · {prediction ? MODEL_LABELS[model] : "fără predicție"}
      </span>
      <div className="featured-actions">
        {prediction &&
          OUTCOMES.map(([outcome, name]) => (
            <span key={outcome} className={`outcome${prediction.most_likely === outcome ? " chosen" : ""}`}>
              {name} <b>{percent(chance(prediction, outcome), 0)}</b>
            </span>
          ))}
        <button className="button primary" onClick={() => onOpen(forecast)}>
          Vezi meciul
        </button>
      </div>
    </LeagueImageCard>
  );
}
