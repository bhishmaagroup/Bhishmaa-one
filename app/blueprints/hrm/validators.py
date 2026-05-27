import datetime

def validate_month_range(month):
    try:
        m = int(month)
        return 1 <= m <= 12
    except (ValueError, TypeError):
        return False

def validate_year_range(year):
    try:
        y = int(year)
        current_year = datetime.date.today().year
        return (current_year - 5) <= y <= (current_year + 2)
    except (ValueError, TypeError):
        return False

def validate_check_times(check_in, check_out):
    if check_in and check_out:
        return check_out >= check_in
    return True
