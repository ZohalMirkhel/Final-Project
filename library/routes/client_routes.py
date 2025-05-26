from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime
from library.models import Book, Checkout
from library import db
# ?ekuteuihsieurhi
client = Blueprint('client', __name__)

# View all available books (with optional search)
@client.route('/catalog')
@login_required
def catalog():
    q = request.args.get('q', '')
    books = Book.query.filter(Book.available == True, Book.title.ilike(f'%{q}%')).all()
    return render_template('client/catalog.html', books=books, query=q)

# Checkout a book
@client.route('/checkout/<int:book_id>')
@login_required
def checkout(book_id):
    book = Book.query.get(book_id)
    if book and book.available:
        book.available = False
        db.session.add(book)
        db.session.commit()

        checkout = Checkout(
            user_id=current_user.id,
            book_id=book_id,
            checkout_date=datetime.utcnow()
        )
        db.session.add(checkout)
        db.session.commit()

    return redirect(url_for('client.catalog'))

# Return a book
@client.route('/return/<int:checkout_id>')
@login_required
def return_book(checkout_id):
    record = Checkout.query.get(checkout_id)
    if record and record.return_date is None and record.user_id == current_user.id:
        record.return_date = datetime.utcnow()
        book = Book.query.get(record.book_id)
        book.available = True
        db.session.commit()
    return redirect(url_for('client.borrowed'))

# View currently borrowed books
@client.route('/borrowed')
@login_required
def borrowed():
    checkouts = Checkout.query.filter_by(user_id=current_user.id, return_date=None).all()
    return render_template('client/borrowed.html', checkouts=checkouts)

# View borrowing history
@client.route('/history')
@login_required
def history():
    checkouts = Checkout.query.filter_by(user_id=current_user.id).all()
    return render_template('client/history.html', checkouts=checkouts)
