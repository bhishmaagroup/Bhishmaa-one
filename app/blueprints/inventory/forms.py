from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, DecimalField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, Optional, ValidationError
from app.blueprints.inventory.validators import validate_sku_format, validate_barcode_format

class ProductForm(FlaskForm):
    name = StringField('Product Name', validators=[DataRequired(), Length(min=2, max=255)])
    sku = StringField('SKU Code (Auto-generated if empty)', validators=[Optional(), Length(max=50)])
    barcode = StringField('Barcode Value', validators=[Optional(), Length(max=50)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=1000)])
    category_id = SelectField('Category', choices=[], default='', validators=[Optional()])
    brand_id = SelectField('Brand', choices=[], default='', validators=[Optional()])
    unit_id = SelectField('Measurement Unit', choices=[], default='', validators=[Optional()])
    
    # Financials
    purchase_price = DecimalField('Purchase Unit Price (₹)', default=0.0, validators=[Optional()])
    selling_price = DecimalField('Selling Unit Price (₹)', default=0.0, validators=[Optional()])
    gst_rate = SelectField('GST Rate (%)', choices=[
        ('0.0', '0% (Exempt)'),
        ('5.0', '5%'),
        ('12.0', '12%'),
        ('18.0', '18%'),
        ('28.0', '28%')
    ], default='18.0')
    
    # Stock Settings
    current_stock = DecimalField('Current Stock Level', default=0.0, validators=[Optional()])
    min_stock_alert = DecimalField('Minimum Stock Alert Level', default=5.0, validators=[Optional()])
    max_stock_level = DecimalField('Maximum Stock Level', default=100.0, validators=[Optional()])
    reorder_quantity = DecimalField('Reorder Quantity', default=20.0, validators=[Optional()])
    is_active = BooleanField('Active', default=True)
    
    submit = SubmitField('Save Product')

    def validate_sku(self, field):
        if field.data and not validate_sku_format(field.data):
            raise ValidationError('SKU can only contain letters, numbers, dashes, and underscores.')

    def validate_barcode(self, field):
        if field.data and not validate_barcode_format(field.data):
            raise ValidationError('Barcode must be alphanumeric.')

class StockAdjustmentForm(FlaskForm):
    quantity_change = DecimalField('Stock Change Quantity (+/-)', validators=[DataRequired()])
    submit = SubmitField('Adjust Stock')
