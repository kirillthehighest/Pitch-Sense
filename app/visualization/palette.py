"""The colours every league shares, for the interface and the charts alike (``docs/brand.md``).

The surfaces are a neutral, almost black night, lighter as they rise (a card is lighter than the
window), never by shadows; each league adds only its accent (``app/ui/themes.py``). The chart
colours each do one job and were checked with a colour-vision validator on the card colour
(2026-10-05, dark mode): the three model colours pass every check for charts where any two lines
can meet (worst colour-blind distance 11.3); the group ramp passes as an ordered ramp.
"""

# Surfaces, from the deepest to the highest (the same as every league's in ``themes.py``)
NIGHT = "#0A0A0C"  # the top bar and the side panel
BACKGROUND = "#0E0E11"  # the window
SURFACE = "#16161A"  # cards and charts
LINE = "#2A2A30"  # borders and dividers
GRID = "#24242A"  # chart gridlines: a hairline one step off the card

# Text (on any surface above: TEXT at least 15:1, MUTED at least 6:1)
TEXT = "#F5F5F7"
MUTED = "#9C9CA6"

# The highlight of a chart as it is built (the chosen season, the chosen team); on screen it takes
# the accent of the league shown (``charts.on_surface``)
GOLD = "#EDBB00"

# Form: win, draw, loss (white letters at least 5.1:1)
WIN = "#157A47"
FORM_DRAW = "#5F5F6A"
LOSS = "#C4314B"

# Charts: identity of the models (categorical, fixed order: never cycled or reassigned)
MODEL_COLOURS = {
    "Elo": "#4D8DFF",
    "Poisson": "#EF5A6F",
    "Logistic regression": "#00A3A8",
}
BASELINE_COLOUR = "#8E929C"  # the reference: neutral grey and dashed, so the models stay in front
WITH_FANS, CLOSED_DOORS = "#4D8DFF", "#EF5A6F"  # a validated pair, for the home advantage chart

# Charts: the K-Means groups are ordered (0 = strongest), so one hue, brightest for the strongest
GROUP_COLOURS = {0: "#D2E2FF", 1: "#8EB4FF", 2: "#5585F0", 3: "#3A63C9"}

# Charts: magnitude (probabilities, counts), one hue from the card's dark to light
SEQUENTIAL = ("#1C2A52", "#24407F", "#2F5DB8", "#4D80EC", "#8EB4FF", "#DCE8FF")
