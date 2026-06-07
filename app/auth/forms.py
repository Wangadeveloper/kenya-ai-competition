from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, IntegerField, FloatField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Optional
from app.models.sql_models import User

class LoginForm(FlaskForm):
    username = StringField('Username or Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    role = SelectField('Register As', choices=[('farmer', 'Farmer / Mkulima'), ('officer', 'Field Officer')], validators=[DataRequired()])
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match')])
    
    full_name = StringField('Full Name', validators=[DataRequired()])
    phone_number = StringField('Phone Number', validators=[DataRequired()])
    county = StringField('County', validators=[DataRequired()])
    sub_county = StringField('Sub-County', validators=[Optional()])
    age = IntegerField('Age', validators=[Optional()])
    gender = SelectField('Gender', choices=[('Male', 'Male'), ('Female', 'Female')], validators=[Optional()])
    
    # CRITICAL: These MUST have Optional() so they don't block submission when roles change!
    farm_size = FloatField('Farm Size', validators=[Optional()])
    primary_crop = StringField('Primary Crop', validators=[Optional()])
    livestock_type = StringField('Livestock', validators=[Optional()])
    water_source = StringField('Water Source', validators=[Optional()])
    employee_id = StringField('Employee ID', validators=[Optional()])
    
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('This username is already taken. Please choose another.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('An account with this email address already exists.')
            
    def validate_employee_id(self, employee_id):
        if self.role.data == 'officer' and not employee_id.data:
            raise ValidationError('Field Officers must provide a valid official badge identifier.')
        if employee_id.data:
            user = User.query.filter_by(employee_id=employee_id.data).first()
            if user:
                raise ValidationError('This Employee Badge ID is already associated with another account.')