"""The project's data periods, shared by calibration and evaluation.

Warm-up seasons only build ratings and history. Calibration seasons are used to choose
hyperparameters. Results are reported only from the first evaluation season onwards, and the
evaluation seasons are never used to choose anything.
"""

WARM_UP_SEASONS = ("2006-07",)
CALIBRATION_SEASONS = ("2007-08", "2008-09", "2009-10")
FIRST_EVALUATION_SEASON = "2010-11"
