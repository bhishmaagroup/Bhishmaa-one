from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from app.blueprints.dashboard.forms import DashboardFilterForm
from app.blueprints.dashboard.services import get_dashboard_data
from app.blueprints.dashboard.permissions import dashboard_view_required

dashboard_bp = Blueprint(
    'dashboard',
    __name__,
    template_folder='templates',
    static_folder='static'
)

@dashboard_bp.route('/', methods=['GET', 'POST'])
@login_required
@dashboard_view_required
def index():
    """
    Renders main dashboard overview panel.
    """
    form = DashboardFilterForm()
    range_select = '30days'
    
    if form.validate_on_submit():
        range_select = form.range_select.data
    else:
        # Check GET parameter fallback
        range_select = request.args.get('range', '30days')
        form.range_select.data = range_select
        
    dashboard_data = get_dashboard_data(current_user.organization_id, range_select)
    
    return render_template(
        'dashboard/index.html',
        widgets=dashboard_data['widgets'],
        chart_labels=dashboard_data['chart_labels'],
        chart_values=dashboard_data['chart_values'],
        alerts=dashboard_data['alerts'],
        transactions=dashboard_data['transactions'],
        form=form
    )
