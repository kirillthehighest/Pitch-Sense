"""Numbers, dates and seasons written the Romanian way, for everything the user reads.

Romanian uses a decimal comma (0,5776; 53,4%), dates as day.month.year (26.10.2025) and, in this
project, seasons as 2006/07. Values are stored and computed in the usual form; only the text shown
on screen and in charts goes through these functions.
"""

from datetime import date


def number(value: float | None, digits: int = 4) -> str:
    """A number with a decimal comma; ``None`` (not available) is shown as a dash."""
    if value is None:
        return "–"
    return f"{value:.{digits}f}".replace("-", "−").replace(".", ",")


def signed(value: float, digits: int = 4) -> str:
    """A number that always shows its sign, for differences: +0,0051 or −0,0073."""
    text = f"{value:+.{digits}f}".replace(".", ",")
    return text.replace("-", "−")


def percent(value: float, digits: int = 1) -> str:
    """A share as a percentage with a decimal comma: 0.534 -> 53,4%."""
    return f"{100 * value:.{digits}f}%".replace("-", "−").replace(".", ",")


def integer(value: int) -> str:
    """A whole number with a dot between thousands, as Romanian writes it: 28.893."""
    return f"{value:,}".replace(",", ".")


def date_text(day: date) -> str:
    """A date as day.month.year: 26.10.2025."""
    return day.strftime("%d.%m.%Y")


def season_text(season: str) -> str:
    """A season label as written in the documentation: 2006-07 -> 2006/07."""
    return season.replace("-", "/")


def quantity(count: int, one: str, many: str) -> str:
    """A count with its noun, by the Romanian rule: 1 meci, 19 meciuri, 38 de meciuri.

    "de" comes between the number and the noun when the last two digits make 20 or more, and for
    round hundreds (100 de meciuri, but 101 meciuri).
    """
    if count == 1:
        return f"1 {one}"
    tail = count % 100
    joiner = " de " if tail >= 20 or (tail == 0 and count != 0) else " "
    return f"{integer(count)}{joiner}{many}"
