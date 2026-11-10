# Defines the maximum number of continuous working days a member can have
MAX_CONTINUOUS_WORKING_DAYS = 5
# Defines the minimum number of C shifts a member has to do in a month
MIN_C_PER_MEMBER = 3
# Defines the maximum number of C shifts a member can do in a month
MAX_C_PER_MEMBER = 5


MAX_C_PER_DAY = 1

# Maximum number of G shifts a member can do in a month
MAX_G_PER_MEMBER = 4

# Maximum number of people in each of A, B and G on a Saturday or Sunday
WEEKEND_MAX_PER_SHIFT = 2

# Maximum time the CP-SAT solver may spend generating one roster.
# Easy months usually finish well before this; it's an upper bound.
SOLVER_TIME_LIMIT_SECONDS = 60