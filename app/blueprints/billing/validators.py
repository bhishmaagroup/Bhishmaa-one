import re

def validate_gstin_format(gstin):
    """
    Validates Indian GSTIN format (15 characters).
    Format: 2 digits state code, 10 alphanumeric PAN, 1 alphanumeric entity code, 
            'Z' default character, 1 check digit.
    """
    if not gstin:
        return True  # Optional field
    pattern = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")
    return bool(pattern.match(gstin.upper()))

def validate_state_code(state_code):
    """
    Validates Indian State Code (2-digit string e.g. '07' for Delhi, '27' for Maharashtra).
    """
    if not state_code:
        return False
    pattern = re.compile(r"^[0-9]{2}$")
    return bool(pattern.match(state_code))
