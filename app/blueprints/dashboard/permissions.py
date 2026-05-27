from functools import wraps
from flask import abort
from flask_login import current_user

def dashboard_view_required(f):
    """
    Decorator to check if user has permission to view the dashboard.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.has_permission('can_view_dashboard'):
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
