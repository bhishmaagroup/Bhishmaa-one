# CRM Utilities

def clean_contact_name(name):
    """
    Cleans up customer/supplier name inputs.
    """
    if not name:
        return ""
    return " ".join(name.strip().split())
