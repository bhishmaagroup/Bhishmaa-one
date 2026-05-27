import random
import string

def generate_random_password(length=10):
    """
    Generates a secure temporary alphanumeric password.
    """
    characters = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choice(characters) for i in range(length))
