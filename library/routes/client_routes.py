from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime
from library.models import Book, Checkout
from library import db
client = Blueprint('client', __name__)

# Enhanced catalog with categories
@client.route('/catalog')
@login_required
def catalog():
    q = request.args.get('q', '')
    category = request.args.get('category', '')

    query = Book.query.filter(Book.available == True)

    if q:
        query = query.filter(Book.title.ilike(f'%{q}%'))
    if category:
        query = query.filter(Book.category == category)

    books = query.all()

    # Get all categories
    categories = db.session.query(Book.category).distinct().all()
    categories = [c[0] for c in categories if c[0]]

    return render_template('client/catalog.html',
                           books=books,
                           query=q,
                           categories=categories,
                           selected_category=category)


# Profile page
@client.route('/profile')
@login_required
def profile():
    return render_template('client/profile.html', member=current_user)


# Add to cart
@client.route('/add-to-cart/<int:book_id>', methods=['POST'])
@login_required
def add_to_cart(book_id):
    action = request.form.get('action')  # 'borrow' or 'buy'
    book = Book.query.get(book_id)

    if book:
        # Check if already in cart
        existing = Cart.query.filter_by(
            member_id=current_user.id,
            book_id=book_id,
            action=action
        ).first()

        if not existing:
            cart_item = Cart(
                member_id=current_user.id,
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


# View cart
@client.route('/cart')
@login_required
def view_cart():
    cart_items = Cart.query.filter_by(member_id=current_user.id).all()
    return render_template('client/cart.html', cart_items=cart_items)


# Remove from cart
@client.route('/remove-from-cart/<int:cart_id>')
@login_required
def remove_from_cart(cart_id):
    cart_item = Cart.query.get(cart_id)
    if cart_item and cart_item.member_id == current_user.id:
        db.session.delete(cart_item)
        db.session.commit()
        flash("Removed from cart", category='success')
    return redirect(url_for('client.view_cart'))


# Checkout cart
@client.route('/checkout-cart', methods=['POST'])
@login_required
def checkout_cart():
    cart_items = Cart.query.filter_by(member_id=current_user.id).all()

    for item in cart_items:
        if item.action == 'borrow':
            # Borrow logic
            if item.book and item.book.available:
                item.book.available = False
                checkout = Checkout(
                    user_id=current_user.id,
                    book_id=item.book.id,
                    checkout_date=datetime.utcnow()
                )
                db.session.add(checkout)
        elif item.action == 'buy':
            # Buy logic
            if item.book and item.book.stock > 0:
                item.book.stock -= 1
                sale_transaction = Transaction(
                    book_name=item.book.title,
                    member_name=current_user.member_name,
                    type_of_transaction="sale",
                    amount=item.book.price,
                    date=date.today()
                )
                db.session.add(sale_transaction)

        # Remove from cart
        db.session.delete(item)

    db.session.commit()
    flash("Checkout completed successfully", category='success')
    return redirect(url_for('client.my_books'))


# My Books page
@client.route('/my-books')
@login_required
def my_books():
    # Borrowed books (not returned)
    borrowed = Checkout.query.filter_by(
        user_id=current_user.id,
        return_date=None
    ).all()

    # Purchased books
    purchased = Transaction.query.filter_by(
        member_name=current_user.member_name,
        type_of_transaction="sale"
    ).all()

    return render_template('client/my_books.html',
                           borrowed=borrowed,
                           purchased=purchased)


# Feedback form
@client.route('/feedback', methods=['GET', 'POST'])
@login_required
def feedback():
    form = FeedbackForm()
    if form.validate_on_submit():
        feedback = Feedback(
            member_id=current_user.id,
            content=form.content.data,
            rating=form.rating.data
        )
        db.session.add(feedback)
        db.session.commit()
        flash("Feedback submitted", category='success')
        return redirect(url_for('client.feedbacks'))
    return render_template('client/feedback.html', form=form)


# View all feedbacks
@client.route('/feedbacks')
@login_required
def feedbacks():
    all_feedbacks = Feedback.query.order_by(Feedback.created_at.desc()).all()
    return render_template('client/feedbacks.html', feedbacks=all_feedbacks)