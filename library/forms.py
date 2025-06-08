from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField, TextAreaField, SelectField, FloatField, PasswordField, BooleanField
from wtforms.validators import Length, DataRequired, ValidationError, InputRequired, NumberRange, Email
from library.models import Member, Book, Transaction
from wtforms.fields import EmailField

# form for creating and updating members
class member_form(FlaskForm):

    # check if unique memberName already exists
    def validate_member_name(self, member_name_to_check):
        member = Member.query.filter_by(member_name=member_name_to_check.data).first()
        if member and (not self.obj or member.id != self.obj.id):
            raise ValidationError('Username already exists!')
        if member:
            raise ValidationError('Username already exists! Please try a different Member Name')

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

class ReturnBookForm(FlaskForm):
    book_id = SelectField('Book', coerce=int)
    submit = SubmitField('Return Book')

class EmptyForm(FlaskForm):
    class Meta:
        csrf = True
    submit = SubmitField()

