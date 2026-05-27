from app.blueprints.roles.constants import PERMISSIONS

def get_permission_description(perm_name):
    """
    Returns the human-friendly description of a permission.
    """
    return PERMISSIONS.get(perm_name, "No description provided.")

def list_all_system_permissions():
    """
    Returns list of all available system permissions as (name, description) tuples.
    """
    return [(name, desc) for name, desc in PERMISSIONS.items()]
