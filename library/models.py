from datetime import datetime
from library import db


class Member(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(), nullable=False)
    member_name = db.Column(db.String(), nullable=False, unique=True)
    phone_number = db.Column(db.String(), nullable=False, unique=True)
    to_pay = db.Column(db.Integer(), default=0)
    total_paid = db.Column(db.Integer(), default=0)
    borrowed = db.relationship('Book', secondary='book_borrow', backref='borrower', lazy='dynamic')


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


class Book_borrowed(db.Model):
    __tablename__ = 'book_borrow'

    id = db.Column(db.Integer(), primary_key=True)
    member_id = db.Column(db.Integer(), db.ForeignKey('member.id'))
    book_id = db.Column(db.Integer(), db.ForeignKey('book.id'))
    borrowed_date = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime)

    # Add these relationships
    member = db.relationship('Member', backref='borrows')
    book = db.relationship('Book', backref='borrow_records')


class Transaction(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    book_name = db.Column(db.String())
    member_name = db.Column(db.String())
    type_of_transaction = db.Column(db.String(length=7), nullable=False)
    date = db.Column(db.Date())
    amount = db.Column(db.Float, default=0.0)

    # Add these foreign keys
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'))
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'))

    # Relationships (optional but recommended)
    book = db.relationship('Book', backref='transactions')
    member = db.relationship('Member', backref='transactions')


class Checkout(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    checkout_date = db.Column(db.DateTime, default=datetime.utcnow)
    return_date = db.Column(db.DateTime, nullable=True)
    due_date = db.Column(db.DateTime, nullable=True)  # Added due_date field

    member = db.relationship('Member', backref='checkouts')
    book = db.relationship('Book', backref='checkouts')


class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'))
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'))
    content = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    member = db.relationship('Member', backref='feedbacks')
    book = db.relationship('Book', backref='feedbacks')


class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'))
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'))
    action = db.Column(db.String(10))  # 'borrow' or 'buy'
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    member = db.relationship('Member', backref='cart_items')
    book = db.relationship('Book', backref='in_carts')