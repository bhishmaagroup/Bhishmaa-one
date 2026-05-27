from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, NumberRange


class OpenSessionForm(FlaskForm):
    counter_number = StringField(
        'Counter Number / Register ID',
        default='Counter-1',
        validators=[DataRequired(), Length(min=1, max=50)]
    )
    opening_balance = DecimalField(
        'Opening Cash Balance (₹)',
        default=0.0,
        validators=[DataRequired(), NumberRange(min=0)]
    )
    submit = SubmitField('Open Register Session')


class CloseSessionForm(FlaskForm):
    real_cash_collected = DecimalField(
        'Actual Cash In Drawer (₹)',
        validators=[DataRequired(), NumberRange(min=0)]
    )
    notes = TextAreaField(
        'Reconciliation Notes / Remarks',
        validators=[Optional(), Length(max=500)]
    )
    submit = SubmitField('Close Register Session & Settle')


class StockTransferForm(FlaskForm):
    to_branch_id = SelectField(
        'Destination Branch',
        validators=[DataRequired()]
    )
    notes = TextAreaField(
        'Transfer Notes / Purpose',
        validators=[Optional(), Length(max=500)]
    )
    submit = SubmitField('Create Stock Transfer')
