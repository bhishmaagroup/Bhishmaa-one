from flask import jsonify, request
from flask_login import login_required, current_user
from app.blueprints.dashboard.routes import dashboard_bp
from app.blueprints.dashboard.services import get_dashboard_data
from app.blueprints.dashboard.permissions import dashboard_view_required

@dashboard_bp.route('/api/metrics', methods=['GET'])
@login_required
@dashboard_view_required
def api_get_metrics():
    """
    Returns dashboard metrics and sales charts as JSON.
    """
    range_select = request.args.get('range', '30days')
    data = get_dashboard_data(current_user.organization_id, range_select)
    return jsonify(data), 200
