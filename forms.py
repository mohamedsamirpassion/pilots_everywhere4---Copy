from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, SelectField, DecimalField, DateTimeField, HiddenField, SelectMultipleField, IntegerField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, Optional, ValidationError
from wtforms.widgets import CheckboxInput, ListWidget
from models import User, SERVICE_TYPES

def AtLeastOneRequired(message=None):
    """Custom validator that requires at least one item to be selected from a MultiCheckboxField"""
    if not message:
        message = 'At least one option must be selected.'
    
    def _at_least_one_required(form, field):
        if not field.data or len(field.data) == 0:
            raise ValidationError(message)
    
    return _at_least_one_required

class MultiCheckboxField(SelectMultipleField):
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Repeat Password', 
                             validators=[DataRequired(), EqualTo('password')])
    user_type = SelectField('Account Type', 
                           choices=[('pilot', 'Pilot Car Operator'), ('trucking', 'Trucking Company')],
                           validators=[DataRequired()])
    submit = SubmitField('Register')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Please use a different email address.')

class PilotProfileForm(FlaskForm):
    company_name = StringField('Company Name', validators=[DataRequired(), Length(max=200)])
    contact_name = StringField('Contact Name', validators=[DataRequired(), Length(max=100)])
    phone = StringField('Phone Number', validators=[DataRequired(), Length(max=20)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    services = MultiCheckboxField('Services Offered', 
                                 choices=SERVICE_TYPES, 
                                 validators=[AtLeastOneRequired('Please select at least one service you can provide.')])
    equipment_details = TextAreaField('Equipment Details')
    certifications = TextAreaField('Certifications')
    submit = SubmitField('Save Profile')

class TruckingProfileForm(FlaskForm):
    company_name = StringField('Company Name', validators=[DataRequired(), Length(max=200)])
    contact_name = StringField('Contact Name', validators=[DataRequired(), Length(max=100)])
    phone = StringField('Phone Number', validators=[DataRequired(), Length(max=20)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    dot_number = StringField('DOT Number', validators=[Optional(), Length(max=20)])
    submit = SubmitField('Save Profile')

class LocationShareForm(FlaskForm):
    location_type = SelectField('Location Type', 
                               choices=[('gps', 'Use Current GPS Location'), ('map', 'Select on Map')],
                               validators=[DataRequired()])
    latitude = HiddenField(validators=[DataRequired()])
    longitude = HiddenField(validators=[DataRequired()])
    address = StringField('Address', validators=[Optional()])
    services_available = MultiCheckboxField('Services Available at This Location', 
                                           choices=SERVICE_TYPES, 
                                           validators=[AtLeastOneRequired('Please select at least one service available at this location.')])
    coverage_radius = IntegerField('Coverage Radius (miles)', 
                                  validators=[DataRequired(), NumberRange(min=100, max=700)],
                                  default=300)
    submit = SubmitField('Share Location')

class JobPostForm(FlaskForm):
    pickup_address = StringField('Pickup Address', validators=[DataRequired(), Length(max=500)])
    pickup_latitude = HiddenField()
    pickup_longitude = HiddenField()
    delivery_address = StringField('Delivery Address', validators=[DataRequired(), Length(max=500)])
    delivery_latitude = HiddenField()
    delivery_longitude = HiddenField()
    pickup_datetime = DateTimeField('Pickup Date & Time', 
                                   format='%Y-%m-%dT%H:%M',
                                   validators=[DataRequired()])
    services_required = MultiCheckboxField('Services Required', 
                                          choices=SERVICE_TYPES, 
                                          validators=[AtLeastOneRequired('Please select at least one service required for this job.')])
    rate_per_mile = DecimalField('Rate per Mile ($)', validators=[Optional(), NumberRange(min=0)])
    rate_per_day = DecimalField('Day Rate ($)', validators=[Optional(), NumberRange(min=0)])
    overnight_rate = DecimalField('Overnight Rate ($)', validators=[Optional(), NumberRange(min=0)])
    nogo_rate = DecimalField('NoGo Fee ($)', validators=[Optional(), NumberRange(min=0)])
    allow_rate_mixing = BooleanField('Allow mixing mileage with day rate')
    description = TextAreaField('Additional Details')
    submit = SubmitField('Post Job')

class JobApplicationForm(FlaskForm):
    proposed_rate_per_mile = DecimalField('Proposed Rate per Mile ($)', validators=[Optional(), NumberRange(min=0)])
    proposed_rate_per_day = DecimalField('Proposed Day Rate ($)', validators=[Optional(), NumberRange(min=0)])
    proposed_overnight_rate = DecimalField('Proposed Overnight Rate ($)', validators=[Optional(), NumberRange(min=0)])
    proposed_nogo_rate = DecimalField('Proposed NoGo Fee ($)', validators=[Optional(), NumberRange(min=0)])
    message = TextAreaField('Message to Trucking Company')
    submit = SubmitField('Apply for Job')

class TripRatingForm(FlaskForm):
    rating = SelectField('Rating', 
                        choices=[(1, '1 Star'), (2, '2 Stars'), (3, '3 Stars'), (4, '4 Stars'), (5, '5 Stars')],
                        coerce=int,
                        validators=[DataRequired()])
    review = TextAreaField('Review', validators=[DataRequired(), Length(min=10, max=500)])
    submit = SubmitField('Submit Rating')

class DirectOfferForm(FlaskForm):
    job_id = HiddenField()
    pilot_id = HiddenField()
    rate_per_mile = DecimalField('Rate per Mile ($)', validators=[Optional(), NumberRange(min=0)])
    rate_per_day = DecimalField('Day Rate ($)', validators=[Optional(), NumberRange(min=0)])
    overnight_rate = DecimalField('Overnight Rate ($)', validators=[Optional(), NumberRange(min=0)])
    nogo_rate = DecimalField('NoGo Fee ($)', validators=[Optional(), NumberRange(min=0)])
    allow_rate_mixing = BooleanField('Allow mixing mileage with day rate')
    message = TextAreaField('Message to Pilot')
    submit = SubmitField('Send Offer')

class RateNegotiationForm(FlaskForm):
    application_id = HiddenField()
    counter_rate_per_mile = DecimalField('Counter Rate per Mile ($)', validators=[Optional(), NumberRange(min=0)])
    counter_rate_per_day = DecimalField('Counter Day Rate ($)', validators=[Optional(), NumberRange(min=0)])
    counter_overnight_rate = DecimalField('Counter Overnight Rate ($)', validators=[Optional(), NumberRange(min=0)])
    counter_nogo_rate = DecimalField('Counter NoGo Fee ($)', validators=[Optional(), NumberRange(min=0)])
    message = TextAreaField('Counter Offer Message')
    submit = SubmitField('Send Counter Offer') 