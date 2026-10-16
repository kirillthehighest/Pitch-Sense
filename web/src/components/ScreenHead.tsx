// The head of a screen other than Meciuri (layout A, the team's choice): a slim strip lit by the
// league's image, with the league's flag and name, the screen's title and what it shows.
import { themeFor } from "../theme";
import type { League } from "../types";
import { Flag } from "./Flag";
import { LeagueImageCard } from "./LeagueImage";

interface Props {
  league: League;
  title: string;
  description: string;
}

export function ScreenHead({ league, title, description }: Props) {
  return (
    <LeagueImageCard
      code={league.code}
      top={league.photo_top}
      credit={league.photo_credit}
      brand={themeFor(league.code).brand}
      share={0.5}
      maxWidth={640}
      className="screen-head"
    >
      <div className="screen-head-content">
        <Flag code={league.code} size={44} />
        <div>
          <span className="eyebrow">
            {league.name} · {league.country}
          </span>
          <h1>{title}</h1>
          <p>{description}</p>
        </div>
      </div>
    </LeagueImageCard>
  );
}
