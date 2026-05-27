from functools import wraps
from flask import abort
from flask_login import current_user
from app.blueprints.roles.constants import PERM_MANAGE_ROLES

def role_management_required(f):
    """
    Decorator to check if user has permission to manage roles.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.has_permission(PERM_MANAGE_ROLES):
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def permission_required(permission_name):
    """
    Decorator to check if current user has a specific permission.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.has_permission(permission_name):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator
