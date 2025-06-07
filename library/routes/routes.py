import json

from flask import Blueprint, render_template
from sqlalchemy import desc
from datetime import datetime
from library.models import Feedback

from library.forms import book_form, member_form
from library.models import Book, Member

routes_bp = Blueprint('routes_bp', __name__)

@routes_bp.route('/')
def welcome():
    return render_template('intro.html')

@routes_bp.route('/', methods=['GET', 'POST'])
@routes_bp.route('/home')
def home_page():
    books_to_borrow = Book.query.filter(Book.borrow_stock > 0).all()
    members_can_borrows = Member.query.filter(
        Member.membership_status == 'active',
        Member.membership_expiry > datetime.utcnow()
    ).all()
    books_for_sale = Book.query.filter(Book.stock > 0).all()
    books_to_return = Book.query.filter(Book.borrower).all()
    return render_template('home.html',
                           member_form=member_form(),
                           book_form=book_form(),
                           books_to_borrow=books_to_borrow,
                           members_can_borrow=members_can_borrows,
                           books_for_sale=books_for_sale,
                           books_to_return=books_to_return,
                           book=False)


@routes_bp.route('/reports', methods=['GET', 'POST'])
def report_page():
    books = Book.query.all()
    members = Member.query.all()

    popular_books_title = []
    books_count = []

    sold_books_titles = []
    sold_books_counts = []

    member_paying_most = []
    member_paid = []

    # Get top borrowed books
    popular_books = Book.query.order_by(desc(Book.member_count)).limit(10).all()

    # Get top sold books
    top_sold_books = Book.query.order_by(desc(Book.sales_count)).limit(10).all()

    # Process borrowed books data
    for book in popular_books:
        if book.member_count > 0:
            popular_books_title.append(book.title[0:20])
            books_count.append(book.member_count)

    # Process sold books data
    for book in top_sold_books:
        if book.sales_count and book.sales_count > 0:
            sold_books_titles.append(book.title[:20])
            sold_books_counts.append(book.sales_count)

    popular_books_title = json.dumps(popular_books_title)
    books_count = json.dumps(books_count)
    member_paying_most = json.dumps(member_paying_most)
    member_paid = json.dumps(member_paid)
    sold_books_titles = json.dumps(sold_books_titles)
    sold_books_counts = json.dumps(sold_books_counts)

    return render_template("reports.html",
                           members=len(members),
                           books=len(books),
                           member_paid=member_paid,
                           book_title=popular_books_title,
                           members_name=member_paying_most,
                           book_count=books_count,
                           sold_books_titles=sold_books_titles,
                           sold_books_counts=sold_books_counts)

@routes_bp.route('/feedbacks')
def feedbacks():
    return render_template('client/feedbacks.html', feedbacks=Feedback.query.all())