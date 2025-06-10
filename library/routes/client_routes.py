from flask_mail import Message
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user, logout_user
from datetime import datetime, date, timedelta
from library.models import Book, Checkout, Cart, Feedback, Transaction, Member, Book_borrowed, User, ReturnRequest
from library.forms import EmptyForm, ProfileForm, MembershipForm, ReturnBookForm, FeedbackForm, ChangePasswordForm, PaymentForm
from werkzeug.security import generate_password_hash, check_password_hash
from library import db
from sqlalchemy.sql import exists
import random
from library import mail
client = Blueprint('client', __name__)

DELIVERY_FEE = 5.0
PICKUP_FEE = 5.0

#catalog
@client.route('/catalog')
@login_required
def catalog():
    q = request.args.get('q', '')
    category = request.args.get('category', '')
    form = EmptyForm()

    # Create base query that includes both borrowable and purchasable books
    query = Book.query.filter(
        (Book.available == True) | (Book.stock > 0)
    )

    if q:
        query = query.filter(Book.title.ilike(f'%{q}%'))
    if category:
        query = query.filter(Book.category == category)

    books = query.all()

    # Get distinct categories from all books (not just filtered)
    categories = db.session.query(Book.category).distinct().all()
    categories = [c[0] for c in categories if c[0]]

    return render_template('client/catalog.html',
                           books=books,
                           query=q,
                           categories=categories,
                           selected_category=category,
                           form=form)


@client.route('/client_home')
@login_required
def client_home():
    member = Member.query.filter_by(user_id=current_user.id).first()

    # Check if membership is active and get expiry
    membership_active = False
    membership_expiry = None

    admin_borrowed_books = db.session.query(Book_borrowed.book_id).filter(
        Book_borrowed.return_date.is_(None)
    ).distinct()

    # Get client borrows
    client_borrowed_books = db.session.query(Checkout.book_id).filter(
        Checkout.return_date.is_(None)
    ).distinct()

    if member:
        membership_active = (
                member.membership_status == 'active' and
                member.membership_expiry and
                member.membership_expiry > datetime.utcnow()
        )
        membership_expiry = member.membership_expiry

    # Fetch books for sale and borrowing
    books_for_sale = Book.query.filter(Book.stock > 0).all()
    books_to_borrow = Book.query.filter(Book.borrow_stock > 0).all() if membership_active else []

    # Initialize book lists
    borrowed_books = []
    purchased_books = []

    if member:
        # Get books that are currently borrowed and not returned
        borrowed_books = db.session.query(Checkout, Book) \
            .join(Book, Book.id == Checkout.book_id) \
            .filter(
            Checkout.member_id == member.id,
            Checkout.return_date.is_(None)
        ).all()

        # Get recent purchases by member
        purchased_books = Transaction.query.filter(
            Transaction.member_id == member.id,
            Transaction.type_of_transaction == "sale"
        ).order_by(Transaction.date.desc()).limit(3).all()
    else:
        # For non-members, fetch purchases by user
        purchased_books = Transaction.query.filter(
            Transaction.user_id == current_user.id,
            Transaction.type_of_transaction == "sale"
        ).order_by(Transaction.date.desc()).limit(3).all()

    # Count current borrowings and enforce borrow limit
    borrowed_count = len(borrowed_books)
    borrow_limit = 10

    # Calculate late fees for overdue books
    late_fees = 0.0
    for checkout, book in borrowed_books:
        if checkout.due_date and datetime.utcnow() > checkout.due_date:
            days_late = (datetime.utcnow() - checkout.due_date).days
            late_fees += days_late * 0.50  # $0.50 per day

    # Prepare forms
    membership_form = MembershipForm()
    return_form = ReturnBookForm()
    return_form.book_id.choices = [
        (checkout.book.id, f"{checkout.book.title} (Due: { checkout.due_date.strftime('%Y-%m-%d') if checkout.due_date else 'N/A' })")
        for checkout, book in borrowed_books
    ] or [(0, 'No books to return')]

    # Render the template with all the context
    return render_template(
        'client_home.html',
        member=member,
        membership_active=membership_active,
        membership_expiry=membership_expiry,
        borrowed_books=borrowed_books,
        purchased_books=purchased_books,
        borrowed_count=borrowed_count,
        borrow_limit=borrow_limit,
        late_fees=late_fees,
        books_for_sale=books_for_sale,
        books_to_borrow=books_to_borrow,
        membership_form=membership_form,
        return_form=return_form,
        datetime=datetime
    )

# Profile page
@client.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm()
    password_form = ChangePasswordForm()
    member = Member.query.filter_by(user_id=current_user.id).first()

    membership_fee = member.membership_fee if member else 0
    refund_amount = 0.0

    # Calculate refund if member is active
    if member and member.is_active_member():
        total_days = (member.membership_expiry - member.membership_start).days
        used_days = (datetime.utcnow() - member.membership_start).days
        unused_days = max(0, total_days - used_days)
        refund_amount = (unused_days / total_days) * (member.membership_fee * (total_days / 30)) * 0.5

    if form.validate_on_submit():
        # Update user information
        current_user.name = form.name.data
        current_user.email = form.email.data
        current_user.phone = form.phone.data
        current_user.address = form.address.data

        if member:
            if form.member_name.data != member.member_name:
                existing_member = Member.query.filter(
                    Member.member_name == form.member_name.data,
                    Member.id != member.id
                ).first()
                if existing_member:
                    flash('That username is already taken. Please choose another.', 'danger')
                    return redirect(url_for('client.profile'))

                member.member_name = form.member_name.data
            member.name = form.name.data

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('client.profile'))

    # Pre-fill form with current data
    form.name.data = current_user.name
    form.email.data = current_user.email
    form.phone.data = current_user.phone
    form.address.data = current_user.address

    if member:
        form.member_name.data = member.member_name

    return render_template('client/profile.html',
                           form=form,
                           password_form=password_form,
                           member=member,
                           refund_amount=refund_amount,
                           membership_fee=membership_fee)


@client.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    member = Member.query.filter_by(user_id=current_user.id).first()

    # Calculate refund if active member
    refund_amount = 0.0
    if member and member.is_active_member():
        total_days = (member.membership_expiry - member.membership_start).days
        used_days = (datetime.utcnow() - member.membership_start).days
        unused_days = max(0, total_days - used_days)
        refund_amount = (unused_days / total_days) * (member.membership_fee * (total_days / 30)) * 0.5

        # Record refund transaction
        transaction = Transaction(
            book_name="Membership Refund",
            type_of_transaction="refund",
            amount=-refund_amount,
            date=date.today(),
            user_id=current_user.id
        )
        db.session.add(transaction)

    # Delete all related records
    if member:
        # Delete only this member's records
        Checkout.query.filter_by(member_id=member.id).delete()
        Feedback.query.filter_by(member_id=member.id).delete()
        Transaction.query.filter_by(member_id=member.id).delete()
        db.session.delete(member)

        # Delete only current user's records
    Cart.query.filter_by(user_id=current_user.id).delete()
    Feedback.query.filter_by(user_id=current_user.id).delete()
    Transaction.query.filter_by(user_id=current_user.id).delete()

    # Only delete current user
    user_to_delete = User.query.get(current_user.id)
    if user_to_delete:
        db.session.delete(user_to_delete)

    db.session.commit()
    logout_user()
    flash('Your account has been permanently deleted', 'info')
    return redirect(url_for('login_bp.client_login'))

#Show Client History
@client.route('/history')
@login_required
def history():
    member = Member.query.filter_by(user_id=current_user.id).first()
    checkouts = []
    pending_returns = []

    if member:
        # Completed returns
        checkouts = Checkout.query.filter_by(member_id=member.id).all()

        # Pending returns - only show requests where book hasn't been returned
        pending_returns = ReturnRequest.query.filter(
            ReturnRequest.member_id == member.id,
            ReturnRequest.is_completed == False,
            # Check that the book hasn't been returned in the Checkout table
            ~exists().where(
                (Checkout.id == ReturnRequest.checkout_id) &
                (Checkout.return_date.isnot(None))
            )
        ).options(db.joinedload(ReturnRequest.book)).all()

    # Purchases remain the same
    purchases = Transaction.query.filter(
        ((Transaction.member_id == current_user.id) |
         (Transaction.user_id == current_user.id)),
        Transaction.type_of_transaction == "sale"
    ).all()

    return render_template('client/history.html',
                           checkouts=checkouts,
                           pending_returns=pending_returns,
                           purchases=purchases)

# Add to cart
@client.route('/add-to-cart/<int:book_id>', methods=['POST'])
@login_required
def add_to_cart(book_id):
    action = request.form.get('action')
    member = Member.query.filter_by(user_id=current_user.id).first()
    is_active = member and member.is_active_member()

    if action == 'borrow' and not is_active:
        flash("Only active members can borrow books", 'danger')
        return redirect(url_for('client.catalog'))

    if action == 'borrow' and member:
        current_borrowed = Checkout.query.filter_by(
            member_id=member.id,
            return_date=None
        ).count()

        if current_borrowed >= 10:
            flash("You've reached the maximum of 10 borrowed books. Return some books before borrowing more.", 'danger')
            return redirect(url_for('client.catalog'))

    book = Book.query.get(book_id)

    if book:
        existing = Cart.query.filter_by(
            user_id=current_user.id,  # Changed to user_id
            book_id=book_id,
            action=action
        ).first()

        if not existing:
            cart_item = Cart(
                user_id=current_user.id,  # Changed to user_id
                book_id=book_id,
                action=action
            )
            db.session.add(cart_item)
            db.session.commit()
            flash("Added to cart", category='success')
        else:
            flash("Already in cart", category='info')
    else:
        flash("Book not found", category='danger')

    return redirect(request.referrer)

def is_member(user):
    return hasattr(user, 'membership_status')

def is_active_member(user):
    if hasattr(user, 'membership_status'):
        return user.membership_status == 'active' and user.membership_expiry > datetime.utcnow()
    return False

# View cart
@client.route('/cart')
@login_required
def view_cart():
    payment_form = PaymentForm()
    cart_items = Cart.query.options(db.joinedload(Cart.book)) \
        .filter_by(user_id=current_user.id) \
        .all()
    subtotal = 0.0
    has_borrow_items = False
    form = EmptyForm()

    is_active_member_status = is_active_member(current_user)

    for item in cart_items:
        if item.action == 'buy' and item.book:
            subtotal += item.book.price
        elif item.action == 'borrow':
            has_borrow_items = True

    delivery_fee = DELIVERY_FEE if cart_items else 0.0
    total = subtotal + delivery_fee

    return render_template('client/cart.html',
                           cart_items=cart_items,
                           subtotal=subtotal,
                           delivery_fee=delivery_fee,
                           total=total,
                           payment_form=payment_form,
                           has_borrow_items=has_borrow_items,
                           is_active_member=is_active_member_status,
                           form=form)


# Remove from cart
@client.route('/remove-from-cart/<int:cart_id>')
@login_required
def remove_from_cart(cart_id):
    deleted_count = Cart.query.filter_by(id=cart_id, user_id=current_user.id).delete()
    if deleted_count > 0:
        db.session.commit()
        flash("Removed from cart", category='success')
    else:
        flash("Item not found", category='danger')
    return redirect(url_for('client.view_cart'))


# Checkout cart
@client.route('/checkout-cart', methods=['POST'])
@login_required
def checkout_cart():
    cardholder_name = request.form.get('cardholder_name')
    card_number = request.form.get('card_number')
    expiry_date = request.form.get('expiry_date')
    cvv = request.form.get('cvv')
    cart_items = Cart.query.options(db.joinedload(Cart.book)) \
        .filter_by(user_id=current_user.id) \
        .all()

    borrow_items_in_cart = [item for item in cart_items if item.action == 'borrow']
    num_borrow_in_cart = len(borrow_items_in_cart)
    has_borrow_items = num_borrow_in_cart > 0
    total_amount = 0

    member = Member.query.filter_by(user_id=current_user.id).first()
    is_active_member_status = member and member.is_active_member()

    if not all([cardholder_name, card_number, expiry_date, cvv]):
        flash('Please fill all payment details', 'danger')
        return redirect(url_for('client.view_cart'))

    if len(card_number) not in (15, 16):
        flash('Invalid card number', 'danger')
        return redirect(url_for('client.view_cart'))

    if len(cvv) not in (3, 4):
        flash('Invalid CVV', 'danger')
        return redirect(url_for('client.view_cart'))

    # Borrow limit check
    if num_borrow_in_cart > 0 and member:
        current_borrowed = Checkout.query.filter_by(
            member_id=member.id,
            return_date=None
        ).count()

        if current_borrowed + num_borrow_in_cart > 10:
            flash(
                f"Cannot checkout: You'll exceed the 10-book limit ({current_borrowed} current + {num_borrow_in_cart} new)",
                'danger')
            return redirect(url_for('client.view_cart'))

    # First pass: validate availability
    for item in cart_items:
        if item.action == 'borrow':
            if item.book.borrow_stock < 1:
                flash(f"Book '{item.book.title}' is not available for borrowing", 'danger')
                return redirect(url_for('client.view_cart'))
        elif item.action == 'buy':
            if item.book.stock < 1:
                flash(f"Book '{item.book.title}' is out of stock", 'danger')
                return redirect(url_for('client.view_cart'))

    # Second pass: process items
    for item in cart_items:
        if item.action == 'borrow':
            # Update book availability
            item.book.borrow_stock -= 1
            if item.book.borrow_stock == 0:
                item.book.available = False

            # Update borrow count
            item.book.member_count = (item.book.member_count or 0) + 1

            # Set due date (2 weeks from now)
            due_date = datetime.utcnow() + timedelta(days=14)

            borrow_transaction = Transaction(
                book_name=item.book.title,
                book_id=item.book.id,
                member_id=member.id,
                member_name=member.member_name,
                type_of_transaction="borrow",
                amount=0.0,
                date=date.today()
            )
            db.session.add(borrow_transaction)

            checkout = Checkout(
                member_id=member.id,
                book_id=item.book.id,
                checkout_date=datetime.utcnow(),
                due_date=due_date
            )
            db.session.add(checkout)

        elif item.action == 'buy':
            item.book.stock -= 1
            item.book.sales_count = (item.book.sales_count or 0) + 1

            if current_user.is_member():
                sale_transaction = Transaction(
                    book_name=item.book.title,
                    book_id=item.book.id,
                    member_id=current_user.id,
                    member_name=current_user.name,
                    type_of_transaction="sale",
                    amount=item.book.price,
                    date=date.today()
                )
            else:
                sale_transaction = Transaction(
                    book_id=item.book.id,
                    user_id=current_user.id,
                    member_name=current_user.name,
                    type_of_transaction="sale",
                    amount=item.book.price,
                    date=date.today()
                )
            db.session.add(sale_transaction)
            total_amount += item.book.price

        # Merge and delete the item safely
        item = db.session.merge(item)
        db.session.delete(item)

    # Delivery fee for borrow transactions
    if has_borrow_items:
        if not is_active_member_status:
            flash("You need an active membership to borrow books", "danger")
            return redirect(url_for('client.view_cart'))

        delivery_transaction = Transaction(
            book_name="Delivery Fee",
            member_id=current_user.id,
            member_name=current_user.name,
            type_of_transaction="delivery",
            amount=DELIVERY_FEE,
            date=date.today()
        )
        db.session.add(delivery_transaction)
        total_amount += DELIVERY_FEE

    db.session.commit()
    flash("Checkout completed successfully", category='success')
    return redirect(url_for('client.my_books'))


# My Books page
@client.route('/my-books')
@login_required
def my_books():
    member = Member.query.filter_by(user_id=current_user.id).first()
    current_borrowed = []
    returned_books = []

    if member:
        # To fetch related Book objects
        current_borrowed = db.session.query(Checkout, Book)\
            .join(Book, Book.id == Checkout.book_id)\
            .filter(
                Checkout.member_id == member.id,
                Checkout.return_date.is_(None)
            ).all()

        returned_books = db.session.query(Checkout, Book)\
            .join(Book, Book.id == Checkout.book_id)\
            .filter(
                Checkout.member_id == member.id,
                Checkout.return_date.isnot(None)
            ).all()

    purchased = Transaction.query.filter(
        ((Transaction.member_id == current_user.id) |
         (Transaction.user_id == current_user.id)),
        Transaction.type_of_transaction == "sale"
    ).all()

    return render_template('client/my_books.html',
                           current_borrowed=current_borrowed,
                           returned_books=returned_books,
                           purchased=purchased)

@client.route('/buy-membership', methods=['POST'])
@login_required
def buy_membership():
    months = int(request.form.get('months', 1))
    cardholder_name = request.form.get('cardholder_name')
    card_number = request.form.get('card_number')
    expiry_date = request.form.get('expiry_date')
    cvv = request.form.get('cvv')
    fee_per_month = 20.0

    # Use discounted pricing for known plans
    fee_map = {1: 20, 3: 60, 6: 120, 12: 420}
    total_fee = fee_map.get(months, months * fee_per_month)
    membership_fee = total_fee / months

    # Check if user already has a member record
    member = Member.query.filter_by(phone_number=current_user.phone).first()
    if not all([cardholder_name, card_number, expiry_date, cvv]):
        flash('Please fill all payment details', 'danger')
        return redirect(url_for('client.client_home'))

    if member:
        # Ensure user_id is set
        if not member.user_id:
            member.user_id = current_user.id

        # Renew existing membership
        if member.membership_expiry and member.membership_expiry > datetime.utcnow():
            new_expiry = member.membership_expiry + timedelta(days=30 * months)
        else:
            new_expiry = datetime.utcnow() + timedelta(days=30 * months)

        member.membership_expiry = new_expiry
        member.membership_status = 'active'
    else:
        # Create new member
        start_date = datetime.utcnow()
        expiry_date = start_date + timedelta(days=30 * months)
        member = Member(
            name=current_user.name,
            phone_number=current_user.phone,
            member_name=current_user.name,
            membership_status='active',
            membership_start=start_date,
            membership_expiry=expiry_date,
            membership_fee=membership_fee,
            user_id=current_user.id
        )
        db.session.add(member)

    # Record the transaction
    transaction = Transaction(
        member_name=member.member_name,
        type_of_transaction="membership",
        amount=total_fee,
        date=date.today(),
        member_id=member.id
    )
    db.session.add(transaction)

    db.session.commit()
    flash("Membership purchased successfully!", "success")
    return redirect(url_for('client.client_home'))

#Cancel Membership
@client.route('/cancel-membership', methods=['POST'])
@login_required
def cancel_membership():
    member = Member.query.filter_by(user_id=current_user.id).first()
    if not member:
        return jsonify({'success': False, 'message': 'Membership not found'}), 404

    # Only allow cancellation if membership is active
    if member.membership_status != 'active' or member.membership_expiry < datetime.utcnow():
        return jsonify({'success': False, 'message': 'No active membership to cancel'}), 400

    # Calculate refund
    total_days = (member.membership_expiry - member.membership_start).days
    used_days = (datetime.utcnow() - member.membership_start).days
    unused_days = max(0, total_days - used_days)
    refund_amount = (unused_days / total_days) * (member.membership_fee * (total_days / 30)) * 0.5

    # Delete dependent records first
    Checkout.query.filter_by(member_id=member.id).delete()
    Cart.query.filter_by(user_id=current_user.id).delete()
    Feedback.query.filter_by(member_id=member.id).delete()
    Transaction.query.filter_by(member_id=member.id).delete()

    db.session.delete(member)

    # Record transaction under user instead of member
    transaction = Transaction(
        book_name="Membership Refund",
        type_of_transaction="refund",
        amount=-refund_amount,
        date=date.today(),
        user_id=current_user.id
    )
    db.session.add(transaction)

    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'Membership cancelled. Refund amount: ${refund_amount:.2f}'
    })

@client.route('/return-book', methods=['POST'])
@login_required
def return_book():
    book_id = request.form.get('book_id')
    member = Member.query.filter_by(user_id=current_user.id).first()

    book = Book.query.get(book_id)
    if not book:
        flash("Book not found.", "danger")
        return redirect(url_for('client.client_home'))

    if not member:
        flash("You don't have an active membership", "danger")
        return redirect(url_for('client.client_home'))

    checkout = Checkout.query.filter_by(
        book_id=book_id,
        member_id=member.id,
        return_date=None
    ).first()

    if not checkout:
        flash("You haven't borrowed this book", "danger")
        return redirect(url_for('client.client_home'))

    # Check if return request already exists
    existing_request = ReturnRequest.query.filter_by(
        checkout_id=checkout.id,
        is_completed=False
    ).first()

    if existing_request:
        flash("Return request for this book is already pending", "info")
        return redirect(url_for('client.client_home'))

    # Calculate late fee
    late_fee = 0.0
    if checkout.due_date and datetime.utcnow() > checkout.due_date:
        days_late = (datetime.utcnow() - checkout.due_date).days
        late_fee = days_late * 0.50

    # Schedule pickup in 2-4 days
    pickup_days = random.randint(2, 4)  # Random between 2-4 days
    pickup_date = datetime.utcnow() + timedelta(days=pickup_days)

    # Create return request
    return_request = ReturnRequest(
        member_id=member.id,
        book_id=book_id,
        checkout_id=checkout.id,
        pickup_date=pickup_date,
        late_fee=late_fee,
        pickup_fee=PICKUP_FEE
    )
    db.session.add(return_request)

    # Record transactions
    if late_fee > 0:
        late_transaction = Transaction(
            member_name=member.member_name,
            type_of_transaction="late_fee",
            amount=late_fee,
            date=date.today(),
            member_id=member.id
        )
        db.session.add(late_transaction)

    pickup_transaction = Transaction(
        book_name=book.title if book else '',
        member_name=member.member_name,
        type_of_transaction="pickup_fee",
        date=date.today(),
        amount=PICKUP_FEE,
        book_id=book.id if book else None,
        member_id=member.id
    )
    db.session.add(pickup_transaction)

    db.session.commit()

    # Send email with pickup date
    user_info = {
        "name": current_user.name,
        "email": current_user.email,
        "phone": current_user.phone,
        "address": current_user.address
    }

    book_info = {
        "title": book.title if book else "N/A",
        "isbn": book.isbn if book else "N/A"
    }

    send_pickup_notification(
        user_info,
        book_info,
        checkout.due_date.strftime('%Y-%m-%d') if checkout.due_date else 'N/A',
        pickup_date.strftime('%Y-%m-%d')
    )

    flash(f"Return requested! Book will be picked up on {pickup_date.strftime('%Y-%m-%d')}.", "success")
    return redirect(url_for('client.client_home'))


def send_pickup_notification(user_info, book_info, due_date, pickup_date):
    subject = f"Book Pickup Scheduled: {book_info['title']}"
    recipient = "zohalmirkhel@gmail.com"

    body = f"""
    A book return has been scheduled:

    User Details:
      Name: {user_info['name']}
      Email: {user_info['email']}
      Phone: {user_info['phone']}
      Address: {user_info['address']}

    Book Details:
      Title: {book_info['title']}
      ISBN: {book_info['isbn']}
      Due Date: {due_date}
      Scheduled Pickup: {pickup_date}

    Please pick up the book on the scheduled date.
    """

    msg = Message(subject=subject, recipients=[recipient], body=body)
    mail.send(msg)

# Feedback form
@client.route('/feedback', methods=['GET', 'POST'])
@login_required
def feedback():
    form = FeedbackForm()
    if form.validate_on_submit():
        # Create feedback based on user type
        if current_user.is_member():
            feedback = Feedback(
                member_id=current_user.id,
                content=form.content.data,
                rating=form.rating.data
            )
        else:
            feedback = Feedback(
                user_id=current_user.id,
                content=form.content.data,
                rating=form.rating.data
            )

        db.session.add(feedback)
        db.session.commit()
        flash("Feedback submitted", category='success')
        return redirect(url_for('client.feedback'))

    # Get all feedbacks with user/member information
    feedbacks = Feedback.query.options(
        db.joinedload(Feedback.member),
        db.joinedload(Feedback.user)
    ).order_by(Feedback.created_at.desc()).all()

    return render_template('client/feedback.html',
                           form=form,
                           feedbacks=feedbacks,
                           current_user=current_user)

@client.route('/feedbacks')
@login_required
def feedbacks():
    feedbacks = Feedback.query.all()
    return render_template('client/feedbacks.html', feedbacks=feedbacks)


@client.route('/change-password', methods=['POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not check_password_hash(current_user.password, form.current_password.data):
            flash("Current password is incorrect", "danger")
            return redirect(url_for('client.profile'))

        # Additional validation for new password
        if len(form.new_password.data) < 8:
            flash("Password must be at least 8 characters", "danger")
            return redirect(url_for('client.profile'))

        if not any(char in '!@#$%^&*(),.?":{}|<>' for char in form.new_password.data):
            flash("Password must contain at least one special character", "danger")
            return redirect(url_for('client.profile'))

        current_user.password = generate_password_hash(form.new_password.data)
        db.session.commit()
        flash("Password updated successfully!", "success")
    else:
        # Handle WTForms validation errors
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error: {error}", "danger")

    return redirect(url_for('client.profile'))