import requests
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from sqlalchemy import or_
from library.models import Transaction
from datetime import datetime
from library.models import Book, Member, Book_borrowed, Checkout
from library import db
from library.forms import book_form, ReturnBookForm, EmptyForm

book_bp = Blueprint('book_bp', __name__)


@book_bp.route('/books', methods=['GET', 'POST'])
def books_page():
    books = Book.query.order_by(Book.id).all()
    form_book = book_form()

    books_to_borrow = Book.query.filter(Book.borrow_stock > 0).all()

    members_can_borrows = Member.query.filter(
        Member.membership_status == 'active',
        Member.membership_expiry > datetime.utcnow()
    ).all()

    # Get admin borrows
    admin_borrowed_books = db.session.query(Book_borrowed.book_id).filter(
        Book_borrowed.return_date.is_(None)
    ).distinct()

    # Get client borrows
    client_borrowed_books = db.session.query(Checkout.book_id).filter(
        Checkout.return_date.is_(None)
    ).distinct()

    # Combine both
    all_borrowed_book_ids = admin_borrowed_books.union(client_borrowed_books).subquery()
    books_to_return = db.session.query(Book).join(
        Book_borrowed, Book.id == Book_borrowed.book_id
    ).filter(
        Book_borrowed.return_date.is_(None)
    ).union(
        db.session.query(Book).join(
            Checkout, Book.id == Checkout.book_id
        ).filter(
            Checkout.return_date.is_(None)
        )
    ).all()

    if form_book.validate_on_submit():
        book_to_create = Book(
            title=form_book.title.data,
            isbn=form_book.isbn.data,
            author=form_book.author.data,
            category=form_book.category.data,
            stock=form_book.stock.data,
            borrow_stock=form_book.stock.data,
            price=form_book.price.data
        )
        db.session.add(book_to_create)
        db.session.commit()
        flash('Successfully created a book', category="success")
        return redirect(url_for('book_bp.books_page'))

    if form_book.errors:
        for err_msgs in form_book.errors.values():
            for err_msg in err_msgs:
                flash(f'Error creating book: {err_msg}', category='danger')

    return_form = ReturnBookForm()

    return render_template('books/books.html',
                           book_form=form_book,
                           books=books,
                           books_to_borrow=books_to_borrow,
                           members_can_borrow=members_can_borrows,
                           books_to_return=books_to_return,
                           return_form=return_form)


@book_bp.route('/delete-book/<int:book_id>', methods=['POST'])
def delete_book(book_id):
    form = EmptyForm()  # Create an instance of your EmptyForm (which includes CSRF protection)
    if form.validate_on_submit():  # This will validate the CSRF token
        book = Book.query.get_or_404(book_id)
        try:
            db.session.delete(book)
            db.session.commit()
            flash("Deleted successfully", category="success")
        except Exception as e:
            flash(f"Deletion error: {str(e)}", category="danger")
    else:
        flash("Invalid request", category="danger")
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
        if request.form.get("price"):
            book.price = float(request.form.get("price"))
        if request.form.get("category"):
            book.category = request.form.get("category")
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


@book_bp.route('/book/<int:book_id>')
def get_book_members(book_id):
    book = Book.query.get_or_404(book_id)
    members = []

    # Admin borrows
    for borrow in book.borrow_records:
        if borrow.return_date is None:
            members.append({
                'id': borrow.member.id,
                'member_name': borrow.member.member_name,
                'borrowed_date': borrow.borrowed_date.strftime('%Y-%m-%d'),
                'due_date': borrow.due_date.strftime('%Y-%m-%d')
            })

    # Client borrows
    for checkout in book.checkouts:
        if checkout.return_date is None:
            members.append({
                'id': checkout.member.id,
                'member_name': checkout.member.member_name,
                'borrowed_date': checkout.checkout_date.strftime('%Y-%m-%d'),
                'due_date': checkout.due_date.strftime('%Y-%m-%d')
            })

    return jsonify({'members': members})


@book_bp.route('/purchase-book', methods=['POST'])
def purchase_book():
    title = request.form.get("title")
    author = request.form.get("author")
    isbn = request.form.get("isbn")
    category = request.form.get("category")
    price = float(request.form.get("price"))

    new_book = Book(
        title=title,
        author=author,
        isbn=isbn,
        category=category,
        stock=1,
        borrow_stock=1
    )

    purchase_transaction = Transaction(
        book_name=title,
        member_name="Library Purchase",
        type_of_transaction="purchase",
        amount=-price,  # Negative amount for expense
        date=date.today()
    )

    db.session.add(new_book)
    db.session.add(purchase_transaction)
    db.session.commit()

    flash("Book purchased and added to library", category='success')
    return redirect(url_for('book_bp.books_page'))

@book_bp.route('/import-from-frappe', methods=['POST'])
def import_books_from_frappe():
    title = request.form.get('title')
    category = request.form.get('category')
    try:
        price = float(request.form.get('price'))
    except (TypeError, ValueError):
        flash("Invalid price provided", category='danger')
        return redirect(url_for('book_bp.books_page'))

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
                    category=category,          # Add category
                    price=price,                # Add price
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

@book_bp.route('/book-checkouts/<int:book_id>')
def get_book_checkouts(book_id):
    book = Book.query.get_or_404(book_id)
    checkouts = []
    for checkout in book.checkouts:
        if checkout.return_date is None:
            checkouts.append({
                'member_id': checkout.member.id,
                'member_name': checkout.member.member_name,
                'borrowed_date': checkout.checkout_date.strftime('%Y-%m-%d'),
                'due_date': checkout.due_date.strftime('%Y-%m-%d')
            })
    return jsonify({'checkouts': checkouts})