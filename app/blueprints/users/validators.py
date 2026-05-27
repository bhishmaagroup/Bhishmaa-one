import re

def validate_phone_format(phone):
    """
    Checks if a string is a valid Indian 10-digit phone number.
    """
    if not phone:
        return True  # Optional field
    pattern = re.compile(r"^[6-9]\d{9}$")
    return bool(pattern.match(phone))
