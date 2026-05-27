from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField
from app.blueprints.dashboard.constants import DATE_RANGES

class DashboardFilterForm(FlaskForm):
    range_select = SelectField('Date Range', choices=DATE_RANGES, default='30days')
    submit = SubmitField('Filter')
