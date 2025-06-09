import json
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import desc
from datetime import datetime
from library.models import Feedback
from library.forms import book_form, member_form, LoginForm, AdminCreateMemberForm
from library.models import Book, Member
from library import app, db

routes_bp = Blueprint('routes_bp', __name__)


@routes_bp.route('/')
def welcome():
    return render_template('intro.html')


from library.forms import AdminCreateMemberForm, book_form

@routes_bp.route('/home')
@login_required
def home_page():
    books_to_borrow = Book.query.filter(Book.borrow_stock > 0).all()
    members_can_borrows = Member.query.filter(
        Member.membership_status == 'active',
        Member.membership_expiry > datetime.utcnow()
    ).all()
    books_for_sale = Book.query.filter(Book.stock > 0).all()

    from library.models import Book_borrowed, Checkout

    admin_borrowed_books = db.session.query(Book_borrowed.book_id).filter(
        Book_borrowed.return_date.is_(None)
    ).distinct()

    client_borrowed_books = db.session.query(Checkout.book_id).filter(
        Checkout.return_date.is_(None)
    ).distinct()

    all_borrowed_book_ids = admin_borrowed_books.union(client_borrowed_books).subquery()
    books_to_return = Book.query.filter(Book.id.in_(all_borrowed_book_ids)).all()

    # ✅ Create the form instance
    admin_form = AdminCreateMemberForm()

    return render_template(
        'home.html',
        admin_form=admin_form,
        book_form=book_form(),
        books_to_borrow=books_to_borrow,
        members_can_borrow=members_can_borrows,
        books_for_sale=books_for_sale,
        books_to_return=books_to_return,
        book=False
    )

@routes_bp.route('/reports', methods=['GET', 'POST'])
@login_required
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
@login_required
def feedbacks():
    # Redirect non-admin users to client feedbacks
    if current_user.role != 'admin':
        return redirect(url_for('client.feedbacks'))

    return render_template('client/feedbacks.html', feedbacks=Feedback.query.all())