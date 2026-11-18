# Defines the maximum number of continuous working days a member can have
MAX_CONTINUOUS_WORKING_DAYS = 5

# --------------------------------------------------
# C shifts
# --------------------------------------------------

# How many people are on C each day. The TL chooses these per roster
# (weekdays and weekends separately); these are the defaults and the
# allowed range for that choice.
DEFAULT_C_PER_WEEKDAY = 1
DEFAULT_C_PER_WEEKEND = 1
MIN_C_PER_DAY = 1
MAX_C_PER_DAY = 3

# Each member's C count is worked out from the month: total C shifts
# divided by the number of members gives a fair share (e.g. 31 / 8 ->
# 3 or 4). Members may be this many shifts below or above that share;
# the "spread C evenly" soft rule still pushes everyone to the fair share.
C_SHARE_TOLERANCE = 1

# Maximum number of G shifts a member can do in a month
MAX_G_PER_MEMBER = 4

# Maximum number of people in each of A, B and G on a Saturday or Sunday
WEEKEND_MAX_PER_SHIFT = 2

# Maximum time the CP-SAT solver may spend generating one roster.
# Easy months usually finish well before this; it's an upper bound.
SOLVER_TIME_LIMIT_SECONDS = 60