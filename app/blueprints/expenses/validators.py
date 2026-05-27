def validate_amount(amount):
    try:
        val = float(amount)
        return val > 0
    except (ValueError, TypeError):
        return False
