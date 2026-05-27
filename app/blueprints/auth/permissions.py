from functools import wraps
from flask import abort, request
from flask_login import current_user
from app.blueprints.auth.utils import verify_jwt_token

def require_permission(permission_name):
    """
    Decorator to enforce permission checks on view routes.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if not current_user.has_permission(permission_name):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def token_required(f):
    """
    Decorator to enforce JWT token authorization headers on API endpoints.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return {'message': 'Missing authorization token'}, 401
            
        token = auth_header.split(" ")[1]
        data = verify_jwt_token(token)
        if not data:
            return {'message': 'Invalid or expired authorization token'}, 401
            
        # Re-expose decoded identity inside request context
        request.user_id = data.get('sub')
        request.organization_id = data.get('org')
        
        return f(*args, **kwargs)
    return decorated_function
