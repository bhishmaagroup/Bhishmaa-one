from flask import Blueprint

hrm_bp = Blueprint(
    'hrm',
    __name__,
    template_folder='templates',
    static_folder='static'
)

# Import routes and api to register endpoints on blueprint
from app.blueprints.hrm import routes
from app.blueprints.hrm import api
