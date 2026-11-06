// The head of a screen other than Meciuri (layout A, the team's choice). Since Phase 25 each
// screen has its own: Predicții a slim strip lit by the league's image; Analiză the league's deep
// colour with the three models in their identity colours, the screen's subject; Clasament the
// stadium of the league's leader (in Standings); Echipe the club's own head (in Team).
import { MODEL_COLOURS, themeFor } from "../theme";
import type { League } from "../types";
import { MODEL_LABELS, MODELS } from "../types";
import { Flag } from "./Flag";
import { LeagueImageCard } from "./LeagueImage";
import { StadiumPhoto } from "./StadiumPhoto";

interface Props {
  league: League;
  title: string;
  description: string;
  variant?: "league" | "lab";
}

export function ScreenHead({ league, title, description, variant = "league" }: Props) {
  const content = (
    <div className="screen-head-content">
      <Flag code={league.code} size={44} />
      <div>
        <h1>
          {title} <span className="h1-league">{league.name}</span>
        </h1>
        <p>{description}</p>
      </div>
      {variant === "lab" && (
        <ul className="head-models" aria-label="Modelele comparate">
          {MODELS.map((model) => (
            <li key={model}>
              <i style={{ background: MODEL_COLOURS[model] }} />
              {MODEL_LABELS[model]}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
  if (variant === "lab") return <section className="screen-head lab-head">{content}</section>;
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
      {content}
    </LeagueImageCard>
  );
}

/** Clasament's head: the stadium of the club on top of the table behind the title. */
export function StadiumHead({ league, team, title, description }: Props & { team: string | null }) {
  return (
    <section className="screen-head stadium-head">
      {team && <StadiumPhoto team={team} className="beside" />}
      <div className="head-shade" />
      <div className="screen-head-content">
        <Flag code={league.code} size={44} />
        <div>
          <h1>
            {title} <span className="h1-league">{league.name}</span>
          </h1>
          <p>{description}</p>
        </div>
      </div>
      {team && <span className="credit">Stadionul liderului, {team} · Foto: Wikimedia Commons</span>}
    </section>
  );
}
