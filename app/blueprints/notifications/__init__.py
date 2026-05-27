from flask import Blueprint

notifications_bp = Blueprint(
    'notifications',
    __name__,
    template_folder='templates',
    static_folder='static'
)

from app.blueprints.notifications import routes
