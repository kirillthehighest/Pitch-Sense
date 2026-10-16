// Numbers, dates and seasons written the Romanian way, as app/services/formatting.py writes them
// for the window: a decimal comma (0,5776; 53,4%), a dot between thousands (28.893), a true minus
// (−0,0073), dates as day.month.year and seasons as 2006/07.

export const WEEKDAYS = ["lun.", "mar.", "mie.", "joi", "vin.", "sâm.", "dum."];
export const MONTHS = [
  "ian.", "feb.", "mar.", "apr.", "mai", "iun.", "iul.", "aug.", "sept.", "oct.", "nov.", "dec.",
];

export function number(value: number | null, digits = 4): string {
  if (value === null) return "–";
  return value.toFixed(digits).replace("-", "−").replace(".", ",");
}

export function signed(value: number, digits = 4): string {
  const text = value.toFixed(digits).replace(".", ",");
  return value < 0 || Object.is(value, -0) ? text.replace("-", "−") : `+${text}`;
}

export function percent(value: number, digits = 1): string {
  return `${number(100 * value, digits)}%`;
}

export function integer(value: number): string {
  const digits = Math.abs(Math.trunc(value)).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return value < 0 ? `−${digits}` : digits;
}

/** A day of the calendar, from the server's ISO text (2026-10-17), without a time zone. */
export function parseDay(text: string): Date {
  const [year, month, day] = text.split("-").map(Number);
  return new Date(year, month - 1, day);
}

export function isoDay(day: Date): string {
  const month = String(day.getMonth() + 1).padStart(2, "0");
  return `${day.getFullYear()}-${month}-${String(day.getDate()).padStart(2, "0")}`;
}

function weekday(day: Date): number {
  return (day.getDay() + 6) % 7; // Monday first, as Python counts
}

export function dateText(day: Date): string {
  const month = String(day.getMonth() + 1).padStart(2, "0");
  return `${String(day.getDate()).padStart(2, "0")}.${month}.${day.getFullYear()}`;
}

export function shortDateText(day: Date): string {
  return `${WEEKDAYS[weekday(day)]} ${day.getDate()} ${MONTHS[day.getMonth()]}`;
}

const LONG_WEEKDAYS = ["luni", "marți", "miercuri", "joi", "vineri", "sâmbătă", "duminică"];
const LONG_MONTHS = [
  "ianuarie", "februarie", "martie", "aprilie", "mai", "iunie",
  "iulie", "august", "septembrie", "octombrie", "noiembrie", "decembrie",
];

/** duminică, 24 mai 2026 */
export function longDateText(day: Date): string {
  return `${LONG_WEEKDAYS[weekday(day)]}, ${day.getDate()} ${LONG_MONTHS[day.getMonth()]} ${day.getFullYear()}`;
}

export function daysBetween(first: Date, second: Date): number {
  return Math.round((second.getTime() - first.getTime()) / 86_400_000);
}

export function dayName(day: Date, today: Date): string {
  const names: Record<number, string> = { [-1]: "Ieri", 0: "Azi", 1: "Mâine" };
  return names[daysBetween(today, day)] ?? shortDateText(day);
}

export function seasonText(season: string): string {
  return season.replace("-", "/");
}

export function quantity(count: number, one: string, many: string): string {
  if (count === 1) return `1 ${one}`;
  const tail = count % 100;
  const joiner = tail >= 20 || (tail === 0 && count !== 0) ? " de " : " ";
  return `${integer(count)}${joiner}${many}`;
}

export function capitalised(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** Three capital letters for a team without a crest: Barcelona → BAR, Real Madrid → RMA. */
export function abbreviation(team: string): string {
  const words = team
    .split(/\s+/)
    .map((word) => [...word].filter((c) => /\p{L}/u.test(c)).join(""))
    .filter(Boolean);
  if (words.length === 0) return "?";
  if (words.length === 1) return words[0].slice(0, 3).toUpperCase();
  return (words[0][0] + words[1].slice(0, 2)).toUpperCase();
}
