from functools import wraps
from flask import abort
from flask_login import current_user

def inventory_management_required(f):
    """
    Decorator to check if user has permission to manage inventory and products.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.has_permission('can_manage_inventory'):
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
