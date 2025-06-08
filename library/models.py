from datetime import datetime
from flask_login import UserMixin
from library import db


class Member(UserMixin, db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(), nullable=False)
    member_name = db.Column(db.String(), nullable=False, unique=True)
    phone_number = db.Column(db.String(), nullable=False, unique=True)
    membership_expiry = db.Column(db.DateTime, nullable=True)
    membership_status = db.Column(db.String(20), default='inactive')
    cancellation_date = db.Column(db.DateTime, nullable=True)
    refund_amount = db.Column(db.Float, default=0.0)
    membership_start = db.Column(db.DateTime, default=datetime.utcnow)
    membership_fee = db.Column(db.Float, default=20.0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    borrowed = db.relationship('Book', secondary='book_borrow',
                               backref='current_borrowers', lazy='dynamic',
                               overlaps="borrows,borrow_records")

    def get_id(self):
        return str(self.id)

    def is_member(self):
        return True

    def is_active_member(self):
        return (
                self.membership_status == 'active' and
                self.membership_expiry > datetime.utcnow()
        )



class Book(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    title = db.Column(db.String(), nullable=False)
    isbn = db.Column(db.String(), nullable=False)
    author = db.Column(db.String(), nullable=False)
    category = db.Column(db.String(100))
    stock = db.Column(db.Integer(), default=0)
    borrow_stock = db.Column(db.Integer(), default=0)
    member_count = db.Column(db.Integer(), default=0)
    returned = db.Column(db.Boolean(), default=False)
    sales_count = db.Column(db.Integer, default=0)
    price = db.Column(db.Float, default=0.0)
    available = db.Column(db.Boolean(), default=True)


class Book_borrowed(db.Model):
    __tablename__ = 'book_borrow'

    id = db.Column(db.Integer(), primary_key=True)
    member_id = db.Column(db.Integer(), db.ForeignKey('member.id'))
    book_id = db.Column(db.Integer(), db.ForeignKey('book.id'))
    borrowed_date = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime)
    return_date = db.Column(db.DateTime, nullable=True)
    # Add these relationships
    member = db.relationship('Member', backref='admin_borrows',
                             overlaps="borrowed,current_borrowers,borrow_records")
    book = db.relationship('Book', backref='admin_borrow_records',
                           overlaps="borrowed,current_borrowers,borrows")


class Transaction(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    book_name = db.Column(db.String(100), nullable=False, default='')
    member_name = db.Column(db.String())
    type_of_transaction = db.Column(db.String(length=7), nullable=False)
    date = db.Column(db.Date())
    amount = db.Column(db.Float, default=0.0)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'))
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=True)
    delivery_fee = db.Column(db.Float, default=0.0)
    book = db.relationship('Book', backref='transactions')
    member = db.relationship('Member', backref='transactions')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user = db.relationship('User', backref='transactions')



class Checkout(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    checkout_date = db.Column(db.DateTime, default=datetime.utcnow)
    return_date = db.Column(db.DateTime, nullable=True)
    due_date = db.Column(db.DateTime, nullable=True)
    member = db.relationship('Member', backref='client_borrows')
    book = db.relationship('Book', backref='client_checkouts')


class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Add this line
    content = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    member = db.relationship('Member', backref='feedbacks', lazy='joined')
    book = db.relationship('Book', backref='feedbacks', lazy='joined')
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=True)
    user = db.relationship('User', backref='feedbacks', lazy='joined')  # Now correctly defined


class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'))
    action = db.Column(db.String(10))
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='cart_items')
    book = db.relationship('Book', backref='cart_items')


# Add to models.py
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False, unique=True)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    member = db.relationship('Member', backref='user', uselist=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def is_member(self):
        return False

    def is_active_member(self):
        return False

    def get_id(self):
        return str(self.id)

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False