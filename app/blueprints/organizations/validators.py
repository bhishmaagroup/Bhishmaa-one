import re

def validate_gstin_format(gstin):
    """
    Checks if a string matches the standard Indian GSTIN format.
    """
    if not gstin:
        return True  # Optional field
    pattern = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")
    return bool(pattern.match(gstin))

def validate_subdomain_slug(subdomain):
    """
    Ensures subdomain only contains alphanumeric characters or dashes.
    """
    pattern = re.compile(r"^[a-z0-9\-]+$")
    return bool(pattern.match(subdomain))
