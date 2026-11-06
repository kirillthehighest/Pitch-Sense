// Seven days around the chosen one, with arrows to move a week; days without matches are dimmed
// but can still be chosen.
import { capitalised, dayName, isoDay, MONTHS, parseDay, WEEKDAYS } from "../format";
import { ChevronIcon } from "./Icons";

const DAYS = 7;

function chipLines(day: Date, today: Date): [string, string] {
  const name = dayName(day, today);
  const first = ["Azi", "Mâine", "Ieri"].includes(name) ? name : capitalised(WEEKDAYS[(day.getDay() + 6) % 7]);
  return [first, `${day.getDate()} ${MONTHS[day.getMonth()]}`];
}

interface Props {
  day: string;
  today: string;
  matchDays: Set<string>;
  onDay: (day: string) => void;
}

export function DayStrip({ day, today, matchDays, onDay }: Props) {
  const chosen = parseDay(day);
  const now = parseDay(today);
  const shift = (days: number) => {
    const next = new Date(chosen);
    next.setDate(next.getDate() + days);
    return isoDay(next);
  };
  const strip = Array.from({ length: DAYS }, (_, index) => shift(index - Math.floor(DAYS / 2)));
  return (
    <div className="day-strip">
      <button className="round" onClick={() => onDay(shift(-DAYS))} aria-label="O săptămână înapoi">
        <ChevronIcon direction="left" />
      </button>
      {strip.map((iso) => {
        const [first, second] = chipLines(parseDay(iso), now);
        return (
          <button
            key={iso}
            className={`day-chip${iso === day ? " chosen" : ""}${matchDays.has(iso) ? "" : " empty"}`}
            aria-current={iso === day ? "date" : undefined}
            onClick={() => onDay(iso)}
          >
            <span>{first}</span>
            <strong>{second}</strong>
          </button>
        );
      })}
      <button className="round" onClick={() => onDay(shift(DAYS))} aria-label="O săptămână înainte">
        <ChevronIcon direction="right" />
      </button>
      {!strip.includes(today) && (
        <button className="pill today" onClick={() => onDay(today)} aria-keyshortcuts="T" title="Tasta T">
          Azi
        </button>
      )}
    </div>
  );
}
