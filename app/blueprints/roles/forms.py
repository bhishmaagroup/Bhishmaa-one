from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectMultipleField, SubmitField
from wtforms.validators import DataRequired, Length, ValidationError
from app.blueprints.roles.validators import validate_role_name

class RoleForm(FlaskForm):
    name = StringField('Role Name', validators=[DataRequired(), Length(min=3, max=50)])
    description = TextAreaField('Description', validators=[Length(max=255)])
    permissions = SelectMultipleField('Permissions', coerce=str, validators=[DataRequired()])
    submit = SubmitField('Save Role')

    def validate_name(self, field):
        is_valid, err_msg = validate_role_name(field.data)
        if not is_valid:
            raise ValidationError(err_msg)
