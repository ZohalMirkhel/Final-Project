import json

from flask import Blueprint, render_template
from sqlalchemy import desc

from library.forms import book_form, member_form
from library.models import Book, Member

routes_bp = Blueprint('routes_bp', __name__)

@routes_bp.route('/', methods=['GET', 'POST'])
@routes_bp.route('/home')
def home_page():
    books_to_borrow = Book.query.filter(Book.borrow_stock > 0).all()
    members_can_borrows = Member.query.filter(Member.to_pay < 500).all()
    books_to_return = Book.query.filter(Book.borrower).all()
    return render_template('home.html', member_form=member_form(),
                           book_form=book_form(),
                           books_to_borrow=books_to_borrow,
                           members_can_borrow=members_can_borrows,
                           books_to_return=books_to_return, book=False)

@routes_bp.route('/reports', methods=['GET', 'POST'])
def report_page():
    books = Book.query.all()
    members = Member.query.all()

    popular_books_title = []
    books_count = []
    member_paying_most = []
    member_paid = []

    popular_books = Book.query.order_by(desc(Book.member_count)).limit(10).all()
    most_paying_members = Member.query.order_by(desc(Member.total_paid)).limit(10).all()

    for book in popular_books:
        if book.member_count > 0:
            popular_books_title.append(book.title[0:20])
            books_count.append(book.member_count)

    popular_books_title = json.dumps(popular_books_title)
    books_count = json.dumps(books_count)

    for member in most_paying_members:
        if member.total_paid > 0:
            member_paying_most.append(member.member_name)
            member_paid.append(member.total_paid)

    member_paying_most = json.dumps(member_paying_most)
    member_paid = json.dumps(member_paid)

    return render_template("reports.html", members=len(members),
                           books=len(books), member_paid=member_paid,
                           book_title=popular_books_title,
                           members_name=member_paying_most,
                           book_count=books_count)
