import re
from app.blueprints.roles.constants import ROLES

def validate_role_name(name):
    """
    Checks if a role name is valid: alphanumeric/spaces only, 3-50 chars.
    """
    if not name or len(name) < 3 or len(name) > 50:
        return False, "Role name must be between 3 and 50 characters."
    
    # Allow letters, numbers, spaces, and underscores/hyphens
    if not re.match(r"^[a-zA-Z0-9\s_\-]+$", name):
        return False, "Role name can only contain letters, numbers, spaces, underscores, and hyphens."
        
    return True, ""

def is_system_role(name):
    """
    Checks if a role name is a default system role.
    """
    return name in ROLES
