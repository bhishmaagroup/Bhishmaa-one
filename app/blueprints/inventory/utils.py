import random
import string

def generate_auto_sku(product_name):
    """
    Auto-generates a clean SKU if none is provided.
    Format: PROD-INITIALS-XXXX where XXXX is random alphanumeric digits.
    """
    clean_name = "".join([c for c in product_name if c.isalnum()]).upper()
    initials = clean_name[:4] if len(clean_name) >= 4 else clean_name
    random_str = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    
    return f"SKU-{initials}-{random_str}"
