from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField, TextAreaField, SelectField, FloatField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional, NumberRange, InputRequired, Regexp
from library.models import Member, Book, Transaction, User
from flask_login import current_user
from wtforms.fields import EmailField
import re


def validate_password_complexity(form, field):
    password = field.data
    if len(password) < 8:
        raise ValidationError('Password must be at least 8 characters long')
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValidationError('Password must contain at least one special character')

# form for creating and updating members
def validate_member_name(member_name_to_check):
    member = Member.query.filter_by(member_name=member_name_to_check.data).first()
    if member:
        raise ValidationError('Username already exists! Please try a different username')


class member_form(FlaskForm):

    # check if phone number already exists
    def validate_phone_number(self, phone_number_to_check):
        phone = Member.query.filter_by(phone_number=phone_number_to_check.data).first()
        if phone:
            raise ValidationError('Phone Number already exists! Please try a different Phone Number')

    membership_months = IntegerField(label='Membership Months',
                                     validators=[InputRequired(), NumberRange(min=1)])
    membership_fee = FloatField('Membership Fee', validators=[InputRequired(), NumberRange(min=20)])
    name = StringField(label='Name', validators=[Length(min=2, max=30), DataRequired()])
    member_name = StringField(label='Member Name', validators=[Length(min=2, max=30), DataRequired()])
    phone_number = StringField(label='Phone Number', validators=[DataRequired()])
    submit = SubmitField(label='Submit')


# form for creating and updating books
class book_form(FlaskForm):
    # checks if book already exists
    def validate_title(self, title_to_check):
        book = Book.query.filter_by(title=title_to_check.data).first()
        if book:
            raise ValidationError('Book already exists')

    title = StringField('Title', validators=[InputRequired()])
    isbn = StringField('ISBN', validators=[InputRequired()])
    author = StringField('Author', validators=[InputRequired()])
    category = StringField('Category', validators=[InputRequired()])
    price = FloatField('Price', validators=[DataRequired()])
    stock = IntegerField('Stock', validators=[InputRequired()])
    submit = SubmitField('Add Book')


class FeedbackForm(FlaskForm):
    content = TextAreaField('Feedback', validators=[InputRequired()])
    rating = SelectField('Rating', choices=[(1, '1 Star'), (2, '2 Stars'),
                                          (3, '3 Stars'), (4, '4 Stars'),
                                          (5, '5 Stars')], coerce=int)
    submit = SubmitField('Submit')

class LoginForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class MembershipForm(FlaskForm):
    months = SelectField('Months', choices=[
        (1, '1 Month - $20'),
        (3, '3 Months - $60'),
        (6, '6 Months - $120'),
        (12, '1 Year - $240')
    ], coerce=int)
    submit = SubmitField('Buy/Renew Membership')


class ProfileForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[DataRequired()])
    address = StringField('Address', validators=[DataRequired(), Length(min=5, max=200)])
    member_name = StringField('Username', validators=[Optional(), Length(min=2, max=30)])
    submit = SubmitField('Update Profile')

    # Custom validation to ensure unique email/phone
    def validate_email(self, email):
        if email.data != current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('That email is already in use!')

    def validate_phone(self, phone):
        if phone.data != current_user.phone:
            user = User.query.filter_by(phone=phone.data).first()
            if user:
                raise ValidationError('That phone number is already in use!')

# Add to forms.py
class AdminCreateMemberForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[DataRequired()])
    address = StringField('Address', validators=[DataRequired(), Length(min=5, max=200)])
    password = PasswordField('Password', validators=[DataRequired()])
    member_name = StringField('Username', validators=[DataRequired(), Length(min=2, max=30)])
    membership_fee = FloatField('Fee Per Month', validators=[DataRequired(), NumberRange(min=20)], default=20.0)
    membership_months = SelectField('Membership', choices=[
        (1, '1 Month - $20'),
        (3, '3 Months - $60'),
        (6, '6 Months - $120'),
        (12, '1 Year - $240')
    ], coerce=int, default=1)
    submit = SubmitField('Create Member')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already in use!')

    def validate_phone(self, phone):
        user = User.query.filter_by(phone=phone.data).first()
        if user:
            raise ValidationError('Phone number already in use!')


class RegistrationForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=100)])
    phone = StringField('Phone', validators=[DataRequired()])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    address = StringField('Address', validators=[DataRequired(), Length(min=5, max=200)])
    role = SelectField('Role', choices=[('customer', 'Customer')])
    submit = SubmitField('Register')

    def validate_phone(self, phone):
        user = User.query.filter_by(phone=phone.data).first()
        if user:
            raise ValidationError('That phone number is already in use!')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is already in use!')


class ReturnBookForm(FlaskForm):
    book_id = SelectField('Book', coerce=int)
    submit = SubmitField('Return Book')

class EmptyForm(FlaskForm):
    class Meta:
        csrf = True
    submit = SubmitField()

class UpdateMemberForm(FlaskForm):
    name = StringField(label='Name', validators=[Length(min=2, max=30), DataRequired()])
    phone_number = StringField(label='Phone Number', validators=[DataRequired()])
    member_name = StringField(label='Member Name', validators=[Length(min=2, max=30), DataRequired()])
    email = EmailField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField(label='Submit')

# Update ChangePasswordForm
class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=8),
        validate_password_complexity  # Add custom validator
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('new_password', message='Passwords must match')
    ])
    submit = SubmitField('Change Password')

# Update AdminChangePasswordForm
class AdminChangePasswordForm(FlaskForm):
    new_password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=8),
        validate_password_complexity  # Add custom validator
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('new_password', message='Passwords must match')
    ])
    submit = SubmitField('Update Password')

class PaymentForm(FlaskForm):
    cardholder_name = StringField('Cardholder Name', validators=[DataRequired()])
    zip_code = StringField('Zip Code', validators=[Length(min=4, max=10)])
    card_number = StringField('Card Number', validators=[
        DataRequired(),
        Length(min=15, max=16, message='Card number must be 15-16 digits')
    ])
    expiry_date = StringField('Expiration Date (MM/YY)', validators=[
        DataRequired(),
        Regexp(r'^(0[1-9]|1[0-2])\/?([0-9]{2})$', message='Format must be MM/YY')
    ])
    cvv = StringField('CVV/CVC', validators=[
        DataRequired(),
        Length(min=3, max=4, message='CVV must be 3-4 digits')
    ])
    billing_address = StringField('Billing Address (optional)', validators=[Optional()])
    submit = SubmitField('Confirm Payment')