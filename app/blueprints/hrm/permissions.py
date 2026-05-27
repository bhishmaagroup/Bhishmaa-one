from functools import wraps
from flask import abort
from flask_login import current_user

def hrm_management_required(f):
    """
    Decorator to check if user has permission to manage staff and payroll (can_manage_hrm).
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.has_permission('can_manage_hrm'):
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
