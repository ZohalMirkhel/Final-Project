# internal imports
from datetime import date, timedelta, datetime
# external imports
from flask import Blueprint, render_template, redirect, flash, request, url_for
from flask import jsonify

from library import db
from library.models import Book, Member, Transaction, Book_borrowed

# Define the blueprint
transactions_bp = Blueprint('transactions_bp', __name__)

# Route: Transactions Page
@transactions_bp.route('/transactions')
def transactions_page():
    transaction = Transaction.query.filter(
        Transaction.type_of_transaction != 'membership').all()
    books_to_borrow = Book.query.filter(Book.borrow_stock > 0).all()
    members_can_borrows = Member.query.filter(
        Member.membership_status == 'active',
        Member.membership_expiry > datetime.utcnow()
    ).all()
    books_for_sale = Book.query.filter(Book.stock > 0).all()
    books_to_return = Book.query.filter(Book.borrower).all()
    return render_template('transactions/transactions.html',
                           transactions=transaction, length=len(transaction),
                           books_to_borrow=books_to_borrow,
                           members_can_borrow=members_can_borrows,
                           books_to_return=books_to_return,
                           books_for_sale=books_for_sale)

def redirect_back():
    return redirect(request.referrer or url_for('transactions_bp.transactions_page'))


@transactions_bp.route('/borrow-book', methods=['POST'])
def borrow_book():
    try:
        member_id = request.form.get("member_name")
        book_id = request.form.get("book_name")
        borrow_fee = float(request.form.get("borrow_fee", 0))

        # Validate inputs
        if not member_id or not member_id.isdigit():
            flash("Please select a valid member", category='danger')
            return redirect_back()
        if not book_id or not book_id.isdigit():
            flash("Please select a valid book", category='danger')
            return redirect_back()

        member = Member.query.get(int(member_id))
        book = Book.query.get(int(book_id))

        if not book or not member:
            flash("Book or member not found", category='danger')
            return redirect_back()

        # Check if book is available for borrowing
        if book.borrow_stock < 1:
            flash("No copies available for borrowing", category='danger')
            return redirect_back()

        # Check membership status
        if member.membership_status != 'active' or member.membership_expiry < datetime.utcnow():
            flash("Membership has expired. Please renew to borrow books.", category='danger')
            return redirect_back()

        # Check current borrowed books count (NEW VALIDATION)
        current_borrows = Book_borrowed.query.filter_by(member_id=member.id).count()
        if current_borrows >= 10:
            flash("Member has reached the maximum limit of 10 borrowed books", category='danger')
            return redirect_back()

        # Calculate due date (14 days from now)
        due_date = datetime.utcnow() + timedelta(days=14)

        # Create borrow record with dates
        borrow_record = Book_borrowed(
            book_id=book.id,
            member_id=member.id,
            borrowed_date=datetime.utcnow(),
            due_date=due_date
        )
        db.session.add(borrow_record)

        # Update book stock
        book.borrow_stock -= 1
        book.member_count = book.member_count + 1 if book.member_count else 1

        # Create transaction record
        borrow_transaction = Transaction(
            book_name=book.title,
            member_name=member.member_name,
            type_of_transaction="borrow",
            date=date.today(),
            amount=borrow_fee,
            book_id=book.id,
            member_id=member.id
        )
        db.session.add(borrow_transaction)

        db.session.commit()
        flash("Book borrowed successfully. Due date: " + due_date.strftime("%Y-%m-%d"), category='success')
        return redirect_back()

    except Exception as e:
        db.session.rollback()
        flash(f"Error: {str(e)}", category='danger')
        return redirect_back()


# Route: Return Book (Fixed)
@transactions_bp.route('/return-book', methods=['POST'])
def return_book():
    try:
        member_id = request.form.get("member_name")
        book_id = request.form.get("book_name")

        borrow_fee = 0
        late_fee = 0

        # Validate inputs
        if not member_id or not member_id.isdigit():
            flash("Please select a valid member", category='danger')
            return redirect_back()
        if not book_id or not book_id.isdigit():
            flash("Please select a valid book", category='danger')
            return redirect_back()

        member = Member.query.get(int(member_id))
        book = Book.query.get(int(book_id))

        if not member:
            flash("Member not found", category='danger')
            return redirect_back()
        if not book:
            flash("Book not found", category='danger')
            return redirect_back()

        # Find borrow record
        borrow_record = Book_borrowed.query.filter_by(
            book_id=book.id,
            member_id=member.id
        ).first()

        if not borrow_record:
            flash("This member hasn't borrowed this book", category='danger')
            return redirect_back()

        # Calculate late fee if applicable
        if datetime.utcnow() > borrow_record.due_date:
            days_late = (datetime.utcnow() - borrow_record.due_date).days
            late_fee = days_late * 10

        # Remove borrow record
        db.session.delete(borrow_record)

        # Update book stock
        book.borrow_stock += 1

        # Create return transaction
        return_transaction = Transaction(
            book_name=book.title,
            member_name=member.member_name,
            type_of_transaction="return",
            date=date.today(),
            amount=late_fee,
            book_id=book.id,
            member_id=member.id
        )
        db.session.add(return_transaction)

        db.session.commit()

        if late_fee > 0:
            flash(f"Book returned successfully with ${late_fee} late fee", category='warning')
        else:
            flash("Book returned successfully", category='success')

        return redirect_back()

    except Exception as e:
        db.session.rollback()
        flash(f"Error: {str(e)}", category='danger')
        return redirect_back()


@transactions_bp.route('/book/<int:book_id>')
def get_book_details(book_id):
    book = Book.query.get(book_id)
    if not book:
        return jsonify({'error': 'Book not found'}), 404

    borrow_records = []
    # Use the relationship to get borrow records
    for borrow in book.borrow_records:
        borrow_records.append({
            'id': borrow.member.id,
            'member_name': borrow.member.member_name,
            'borrowed_date': borrow.borrowed_date.strftime('%Y-%m-%d'),
            'due_date': borrow.due_date.strftime('%Y-%m-%d')
        })

    return jsonify({
        'book_id': book.id,
        'title': book.title,
        'members': borrow_records
    })

@transactions_bp.route('/sell-book', methods=['POST'])
def sell_book():
    book_id = request.form.get('book_id')
    member_id = request.form.get('member_id')
    price = float(request.form.get('price'))

    book = Book.query.get(book_id)
    member = Member.query.get(member_id)

    if not book:
        flash("Book not found", category="danger")
        return redirect_back()

    if not member:
        flash("Member not found", category="danger")
        return redirect_back()

    if book.stock < 1:
        flash("This book is out of stock", category="danger")
        return redirect_back()

    try:
        book.stock -= 1
        if book.sales_count is None:
            book.sales_count = 1
        else:
            book.sales_count += 1

        sale_transaction = Transaction(
            book_name=book.title,
            member_name=member.member_name,
            type_of_transaction="sale",
            amount=price,
            date=date.today(),
            book_id=book.id,
            member_id=member.id
        )

        db.session.add(sale_transaction)
        db.session.commit()
        flash(f"Successfully sold {book.title}", category="success")
        return redirect_back()
    except Exception as e:
        flash(f"Error: {str(e)}", category="danger")
        return redirect_back()


def redirect_back():
    return redirect(request.referrer or url_for('transactions_bp.transactions_page'))


# Add purchase from member route
@transactions_bp.route('/purchase-book', methods=['POST'])
def purchase_book():
    member_requested = request.form.get("member_name")
    title = request.form.get("title")
    author = request.form.get("author")
    isbn = request.form.get("isbn")
    category = request.form.get("category")
    price = float(request.form.get("price"))

    member = Member.query.get(int(member_requested)) if member_requested and member_requested.isdigit() else None

    # Create new book
    new_book = Book(
        title=title,
        author=author,
        isbn=isbn,
        category=category,
        stock=1,
        borrow_stock=1,
        price=0  # Reset price for library use
    )
    db.session.add(new_book)
    db.session.flush()  # Get the new_book ID

    # Record purchase transaction
    purchase_transaction = Transaction(
        book_name=title,
        member_name=member.member_name if member else "Library Purchase",
        type_of_transaction="purchase",
        amount=-price,  # Negative for expense
        date=date.today(),
        book_id=new_book.id,
        member_id=member.id if member else None
    )
    db.session.add(purchase_transaction)

    db.session.commit()
    flash("Book purchased and added to library", category='success')
    return redirect(request.referrer)