import re

def validate_sku_format(sku):
    """
    Validates Stock Keeping Unit (SKU) format: alphanumeric and dashes/underscores only.
    """
    if not sku:
        return True  # Optional
    pattern = re.compile(r"^[a-zA-Z0-9_\-]+$")
    return bool(pattern.match(sku))

def validate_barcode_format(barcode):
    """
    Validates barcode: alphanumeric only.
    """
    if not barcode:
        return True  # Optional
    pattern = re.compile(r"^[a-zA-Z0-9]+$")
    return bool(pattern.match(barcode))
