"""The PitchSense colours, for the interface and the charts alike (``docs/brand.md``).

A dark theme: the night of a floodlit match, the blue and garnet of the stripes and gold for
whatever the eye should find first. Surfaces get lighter as they rise (a card is lighter than
the window), never by shadows. The chart colours each do one job and were checked with a
colour-vision validator on the card colour (2026-10-05, dark mode): the three model colours pass
every check for charts where any two lines can meet (worst colour-blind distance 11.3); the group
ramp passes as an ordered ramp.
"""

# Surfaces, from the deepest to the highest
NIGHT = "#070B17"  # the top bar and the side panel
BACKGROUND = "#0B1020"  # the window
SURFACE = "#141B30"  # cards and charts
SURFACE_HIGH = "#1C2541"  # table headers, inputs, hover
SURFACE_TOP = "#253052"  # pressed buttons, selected rows, tooltips
LINE = "#2A3557"  # borders and dividers
GRID = "#222B46"  # chart gridlines: a hairline one step off the card

# Text (on any surface above: TEXT at least 13.7:1, MUTED at least 6.7:1)
TEXT = "#F2F4F8"
MUTED = "#A3ADC6"
FAINT = "#6F7A96"  # disabled controls only, never for text that must be read

# Brand: blaugrana adapted to a dark background (the official #004D98 and #A50044 sink into the
# night), and gold, the one accent of a screen
BLAU = "#0B5BB8"
GRANA = "#B3004E"
GOLD = "#EDBB00"  # 10.6:1 on the window; the background of primary buttons, under NIGHT text
GOLD_HOVER = "#FFCB1F"
GOLD_TINT = "#2E2E2A"  # 12% gold over a card: the row of "your team"

# A match: home, draw and away in the probability bars, blue and garnet poles around a neutral
# grey (validated 2026-10-05: worst colour-blind distance 12.9); white text on home and away (at
# least 5.4:1), NIGHT text on the lighter draw (6.1:1)
HOME = "#2B63D9"
DRAW = "#8790A6"
AWAY = "#C2185B"

# Form: win, draw, loss (white letters at least 5.1:1)
WIN = "#157A47"
FORM_DRAW = "#5C6784"
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
