from flask import Blueprint

platform_bp = Blueprint(
    'platform',
    __name__,
    template_folder='templates',
    static_folder='static'
)

# Import routes to register endpoints on the blueprint
from app.blueprints.platform import routes
