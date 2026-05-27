import re

def validate_phone_number(phone):
    """
    Validates standard 10-digit Indian mobile numbers.
    """
    if not phone:
        return True
    pattern = re.compile(r"^[6-9]\d{9}$")
    return bool(pattern.match(phone))

def validate_gst_number(gstin):
    """
    Validates Indian 15-character GSTIN.
    """
    if not gstin:
        return True
    pattern = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")
    return bool(pattern.match(gstin.upper()))
