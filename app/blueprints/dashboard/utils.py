from datetime import datetime, timedelta

def get_datetime_range(range_name):
    """
    Returns start and end datetime objects based on the selected range keyword.
    """
    end_dt = datetime.utcnow()
    
    if range_name == 'today':
        start_dt = datetime(end_dt.year, end_dt.month, end_dt.day)
    elif range_name == 'yesterday':
        yesterday = end_dt - timedelta(days=1)
        start_dt = datetime(yesterday.year, yesterday.month, yesterday.day)
        end_dt = datetime(end_dt.year, end_dt.month, end_dt.day) - timedelta(microseconds=1)
    elif range_name == '7days':
        start_dt = end_dt - timedelta(days=7)
    elif range_name == '30days':
        start_dt = end_dt - timedelta(days=30)
    elif range_name == '12months':
        start_dt = end_dt - timedelta(days=365)
    else:
        # Default to 30 days
        start_dt = end_dt - timedelta(days=30)
        
    return start_dt, end_dt

def format_inr_currency(value):
    """
    Formats numeric value into Indian Rupee currency representation.
    """
    try:
        val = float(value)
        return f"₹ {val:,.2f}"
    except (ValueError, TypeError):
        return "₹ 0.00"
