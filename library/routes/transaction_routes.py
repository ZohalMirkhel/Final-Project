# internal imports
from library import db
from datetime import date

# external imports
from flask import Blueprint, render_template, redirect, url_for, flash, request
from library.models import Book, Member, Transaction, Book_borrowed

# Define the blueprint
transactions_bp = Blueprint('transactions_bp', __name__)

# Route: Transactions Page
@transactions_bp.route('/transactions')
def transactions_page():
    transaction = Transaction.query.order_by('id').all()
    books_to_borrow = Book.query.filter(Book.borrow_stock > 0).all()
    members_can_borrows = Member.query.filter(Member.to_pay < 500).all()
    books_to_return = Book.query.filter(Book.borrower).all()
    return render_template('transactions/transactions.html',
                           transactions=transaction, length=len(transaction),
                           books_to_borrow=books_to_borrow,
                           members_can_borrow=members_can_borrows,
                           books_to_return=books_to_return)

# Route: Borrow Book
@transactions_bp.route('/borrow-book', methods=['GET', 'POST'])
def borrow_book():
    member_requested = request.form.get("member_name")
    book_requested = request.form.get("book_name")
    member = Member.query.get(int(member_requested))
    book = Book.query.get(int(book_requested))

    if book and member:
        member.to_pay += 30
        book.borrow_stock -= 1
        book.member_count += 1
        borrow = Book_borrowed(book=book.id, member=member.id)
        borrow_book = Transaction(book_name=book.title,
                                  member_name=member.member_name,
                                  type_of_transaction="borrow",
                                  amount=0,
                                  date=date.today())
        db.session.add_all([borrow_book, borrow])
        db.session.commit()
        flash("Issued book", category='success')
    else:
        flash("Enter the Value", category='danger')

    return redirect(request.referrer)

# Route: Return Book
@transactions_bp.route('/return-book', methods=['GET', 'POST'])
def return_book():
    member_requested = request.form.get("member_name")
    book_requested = request.form.get("book_name")
    is_paid = request.form.get("paid")
    paid = 30 if is_paid == 'on' else 0

    member = Member.query.get(member_requested)
    book = Book.query.get(book_requested)

    if member and book:
        member.to_pay -= paid
        member.total_paid += paid
        book.borrow_stock += 1
        book.borrower.remove(member)
        return_book = Transaction(book_name=book.title,
                                  member_name=member.member_name,
                                  type_of_transaction="return",
                                  amount=paid,
                                  date=date.today())
        db.session.add(return_book)
        db.session.commit()
        flash(f"Returned book from {member.member_name}", category='success')
    else:
        flash("Error in returning the book", category='danger')

    return redirect(request.referrer)