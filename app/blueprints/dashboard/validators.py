import re
from datetime import datetime
from app.blueprints.dashboard.constants import RANGE_TODAY, RANGE_YESTERDAY, RANGE_WEEK, RANGE_MONTH, RANGE_YEAR

def validate_date_range_name(range_name):
    """
    Validates if range name is one of the supported constants.
    """
    valid_ranges = [RANGE_TODAY, RANGE_YESTERDAY, RANGE_WEEK, RANGE_MONTH, RANGE_YEAR]
    return range_name in valid_ranges

def validate_custom_dates(start_str, end_str):
    """
    Validates if custom dates are correctly formatted (YYYY-MM-DD) and start_date <= end_date.
    """
    if not start_str or not end_str:
        return False, "Both start and end dates are required."
        
    date_regex = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    if not date_regex.match(start_str) or not date_regex.match(end_str):
        return False, "Dates must be in YYYY-MM-DD format."
        
    try:
        start_date = datetime.strptime(start_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_str, "%Y-%m-%d")
        if start_date > end_date:
            return False, "Start date cannot be after end date."
        return True, ""
    except ValueError:
        return False, "Invalid date values."
