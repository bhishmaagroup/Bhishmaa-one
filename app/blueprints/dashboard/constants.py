# Dashboard Module Constants

# Date range filters
RANGE_TODAY = 'today'
RANGE_YESTERDAY = 'yesterday'
RANGE_WEEK = '7days'
RANGE_MONTH = '30days'
RANGE_YEAR = '12months'

DATE_RANGES = [
    (RANGE_TODAY, 'Today'),
    (RANGE_YESTERDAY, 'Yesterday'),
    (RANGE_WEEK, 'Last 7 Days'),
    (RANGE_MONTH, 'Last 30 Days'),
    (RANGE_YEAR, 'Last 12 Months')
]

# Default KPI colors
COLOR_PRIMARY = 'primary'
COLOR_SUCCESS = 'success'
COLOR_WARNING = 'warning'
COLOR_DANGER = 'danger'
COLOR_INFO = 'info'

# CSS styles mapping for UI
KPI_COLORS = [
    COLOR_PRIMARY,
    COLOR_SUCCESS,
    COLOR_WARNING,
    COLOR_DANGER,
    COLOR_INFO
]
