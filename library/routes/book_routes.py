import requests
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from sqlalchemy import or_

from library import db
from library.forms import book_form
from library.models import Book, Member

book_bp = Blueprint('book_bp', __name__)


# Renders book page
@book_bp.route('/books', methods=['GET', 'POST'])
def books_page():
    books = Book.query.order_by('id').all()
    form_book = book_form()
    books_to_borrow = Book.query.filter(Book.borrow_stock > 0).all()
    members_can_borrows = Member.query.filter(Member.to_pay < 500).all()
    books_to_return = Book.query.filter(Book.borrower).all()

    if form_book.validate_on_submit():
        book_to_create = Book(
            title=form_book.title.data,
            isbn=form_book.isbn.data,
            author=form_book.author.data,
            stock=form_book.stock.data,
            borrow_stock=form_book.stock.data
        )
        db.session.add(book_to_create)
        db.session.commit()
        flash('Successfully created a book', category="success")
        return redirect(url_for('book_bp.books_page'))

    if form_book.errors:
        for err_msg in form_book.errors.values():
            flash(f'Error creating book: {err_msg}', category='danger')

    return render_template('books/books.html',
                           book_form=form_book,
                           books=books,
                           books_to_borrow=books_to_borrow,
                           members_can_borrow=members_can_borrows,
                           books_to_return=books_to_return)


@book_bp.route('/delete-book/<int:book_id>', methods=['POST'])
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    try:
        db.session.delete(book)
        db.session.commit()
        flash("Deleted successfully", category="success")
    except Exception as e:
        flash(f"Deletion error: {str(e)}", category="danger")
    return redirect(url_for('book_bp.books_page'))


@book_bp.route('/update-book/<int:book_id>', methods=['POST'])
def update_book(book_id):
    book = Book.query.get_or_404(book_id)
    try:
        if request.form.get("title") and book.title != request.form.get("title"):
            book.title = request.form.get("title")
        if request.form.get("author") and book.author != request.form.get("author"):
            book.author = request.form.get("author")
        if request.form.get("isbn") and book.isbn != request.form.get("isbn"):
            book.isbn = request.form.get("isbn")
        if request.form.get("stock"):
            new_stock = int(request.form.get("stock"))
            book.stock = new_stock
            book.borrow_stock = new_stock  # Or adjust based on your business logic
        db.session.commit()
        flash("Updated successfully", category="success")
    except Exception as e:
        flash(f"Update failed: {str(e)}", category="danger")
    return redirect(url_for('book_bp.books_page'))


@book_bp.route('/search', methods=['POST'])
def search_book():
    query = request.form.get("query")
    books = Book.query.filter(
        or_(
            Book.title.ilike(f'%{query}%'),
            Book.author.ilike(f'%{query}%')
        )).all()
    return render_template('books/search_page.html', books=books)


@book_bp.route('/import-from-frappe', methods=['POST'])
def import_books_from_frappe():
    title = request.form.get('title')
    try:
        response = requests.get(f"https://frappe.io/api/method/frappe-library?page=1&title={title}")
        books_data = response.json()['message']

        imported_count = 0
        for book_data in books_data:
            # Check for existing book by title and author
            exists = Book.query.filter_by(
                title=book_data['title'],
                author=book_data['authors']
            ).first()

            if not exists:
                new_book = Book(
                    title=book_data['title'],
                    isbn=book_data['isbn'],
                    author=book_data['authors'],
                    stock=20,
                    borrow_stock=20
                )
                db.session.add(new_book)
                imported_count += 1

        db.session.commit()
        flash(f"Imported {imported_count} new books", category="success")
    except Exception as e:
        flash(f"Import error: {str(e)}", category="danger")

    return redirect(url_for('book_bp.books_page'))


@book_bp.route('/book/<int:book_id>')
def get_book_members(book_id):
    book = Book.query.get_or_404(book_id)
    members = [{
        'id': member.id,
        'member_name': member.member_name
    } for member in book.borrower]
    return jsonify({'members': members})