from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, FloatField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length

class RegistrationForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(max=150)])
    phone_number = StringField('Phone Number (e.g., +2547...)', validators=[DataRequired(), Length(max=20)])
    password = PasswordField('PIN / Password', validators=[DataRequired(), Length(min=4)])
    county = SelectField('County', choices=[('Bungoma', 'Bungoma'), ('Eldoret', 'Uasin Gishu'), ('Meru', 'Meru'), ('Nakuru', 'Nakuru'), ('Kilifi', 'Kilifi')], validators=[DataRequired()])
    cooperative = StringField('Cooperative/SACCO Name (Optional)')
    farm_size = FloatField('Farm Size (Acres)', validators=[DataRequired()])
    main_crop = StringField('Main Value Crop (e.g., Maize, Beans)', validators=[DataRequired()])
    submit = SubmitField('Register Profile')