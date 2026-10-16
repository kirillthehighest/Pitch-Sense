// The match of the day at the top of the matches screen, as the hero cards of the references:
// the league's image, both teams with their crests in large capitals (and the score once played),
// the day and kickoff, the chosen model's three probabilities and a button to the match's page.
import { capitalised, parseDay, percent, shortDateText } from "../format";
import { themeFor } from "../theme";
import type { Forecast, League, Outcome } from "../types";
import { MODEL_LABELS } from "../types";
import { Crest } from "./Crest";
import { LeagueImageCard } from "./LeagueImage";
import { chance } from "./MatchRow";

const OUTCOMES: [Outcome, string][] = [["H", "Gazde"], ["D", "Egal"], ["A", "Oaspeți"]];

interface Props {
  forecast: Forecast;
  league: League;
  model: string;
  favourite: string | null;
  onOpen: (forecast: Forecast) => void;
}

export function FeaturedMatch({ forecast, league, model, favourite, onOpen }: Props) {
  const prediction = forecast.predictions.find((p) => p.model === model);
  const played = forecast.result !== null;
  let when = capitalised(shortDateText(parseDay(forecast.date)));
  if (forecast.kickoff) when += `, ${forecast.kickoff}`;
  const teams: [string, number | null][] = [
    [forecast.home_team, forecast.home_goals],
    [forecast.away_team, forecast.away_goals],
  ];
  return (
    <LeagueImageCard
      code={league.code}
      top={league.photo_top}
      credit={league.photo_credit}
      brand={themeFor(league.code).brand}
      className="featured"
    >
      <span className="eyebrow">Meciul zilei · {league.name}</span>
      <div className="featured-teams">
        {teams.map(([team, goals]) => (
          <div key={team} className="featured-team">
            <Crest team={team} size={40} ring={team === favourite} />
            <span>{team}</span>
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
