# internal imports
from flask import Blueprint
from flask import render_template, redirect, url_for, flash, request

from library import app, db
from library.forms import member_form
from library.models import Book, Member, Transaction
from datetime import datetime, timedelta, date
from sqlalchemy import or_

# external imports


members_bp = Blueprint('members_bp', __name__)

# Renders member page
@members_bp.route('/members', methods=['GET', 'POST'])
def members_page():
    # Query members once
    members = Member.query.order_by('id').all()

    # Precompute total paid for each member
    for member in members:
        total_paid = Transaction.query.filter_by(
            member_id=member.id,
            type_of_transaction='membership'
        ).with_entities(db.func.sum(Transaction.amount)).scalar() or 0.0
        member.total_paid = total_paid

    form_member = member_form()
    books_to_borrow = Book.query.filter(Book.borrow_stock > 0).all()
    members_can_borrow = Member.query.filter(
        Member.membership_status == 'active',
        Member.membership_expiry > datetime.utcnow()
    ).all()
    books_for_sale = Book.query.filter(Book.stock > 0).all()

    # Fix: Get books that are currently borrowed (both admin and client)
    from library.models import Book_borrowed, Checkout

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
    books_to_return = Book.query.filter(Book.id.in_(all_borrowed_book_ids)).all()
    books_for_sale = Book.query.filter(Book.stock > 0).all()

    if form_member.validate_on_submit():
        start_date = datetime.utcnow()
        expiry_date = start_date + timedelta(days=30 * form_member.membership_months.data)
        member_to_create = Member(
            name=form_member.name.data,
            phone_number=form_member.phone_number.data,
            member_name=form_member.member_name.data,
            membership_status='active',
            membership_start=start_date,
            membership_expiry=expiry_date,
            membership_fee=form_member.membership_fee.data
        )
        db.session.add(member_to_create)
        db.session.commit()

        # Record initial membership fee transaction AFTER member is created
        initial_fee = form_member.membership_fee.data * form_member.membership_months.data
        transaction = Transaction(
            member_name=member_to_create.member_name,
            type_of_transaction="membership",
            amount=initial_fee,
            date=date.today(),
            member_id=member_to_create.id
        )
        db.session.add(transaction)
        db.session.commit()

        flash('Successfully created a member', category="success")
        return redirect(request.referrer)

    if form_member.errors != {}:
        for err_msg in form_member.errors.values():
            flash(f'Error creating member: {err_msg}', category='danger')

    return render_template('members/members.html',
                           member_form=form_member,
                           members=members,
                           length=len(members),
                           books_to_borrow=books_to_borrow,
                           members_can_borrow=members_can_borrow,
                           books_to_return=books_to_return,
                           books_for_sale=books_for_sale,
                           current_date=datetime.utcnow().date())


# deletes a member
@members_bp.route('/delete-member/<member_id>', methods=['POST'])
def delete_member(member_id):
    try:
        # reads requested member from db
        member = Member.query.filter_by(id=member_id).first()
        db.session.delete(member)
        db.session.commit()
        flash("Deleted Successfully", category="success")

    except:
        flash("Error in deletion", category="danger")

    return redirect(url_for('routes_bp.home_page'))


# updates a member
@members_bp.route('/update-member/<member_id>', methods=['GET', 'POST'])
def update_member(member_id):
    # reads requested member from db
    member = Member.query.filter_by(id=member_id).first()
    newName = request.form.get("name")
    newNumber = request.form.get("phone_number")
    newMember = request.form.get("member_name")

    try:
        if member.name is not newName:
            member.name = newName
        if member.phone_number is not newNumber:
            member.phone_number = newNumber
        if member.member_name is not newMember:
            member.member_name = newMember
        db.session.commit()
        flash("Updated Successfully!", category="success")

    except:
        flash("Failed to update", category="danger")

    return redirect(url_for('members_bp.members_page'))


@members_bp.route('/renew-membership/<member_id>', methods=['POST'])
def renew_membership(member_id):
    member = Member.query.get(member_id)
    if not member:
        flash("Member not found", category="danger")
        return redirect(url_for('members_bp.members_page'))

    # Get the fee per month (default to 20.0 if not set)
    fee_per_month = float(request.form.get('fee', 20.0))
    months = int(request.form.get('months', 1))
    cost = months * fee_per_month

    # Calculate new expiry date
    if member.membership_expiry and member.membership_expiry > datetime.utcnow():
        new_expiry = member.membership_expiry + timedelta(days=30 * months)
    else:
        new_expiry = datetime.utcnow() + timedelta(days=30 * months)

    # Update membership details
    member.membership_expiry = new_expiry
    member.membership_status = 'active'

    # Record transaction
    transaction = Transaction(
        member_name=member.member_name,
        type_of_transaction="membership",
        amount=cost,
        date=date.today(),
        member_id=member.id
    )

    db.session.add(transaction)
    db.session.commit()

    flash(f"Membership renewed for {months} month(s). New expiry: {new_expiry.strftime('%Y-%m-%d')}",
          category='success')
    return redirect(url_for('members_bp.members_page'))


@members_bp.route('/cancel-membership/<member_id>', methods=['POST'])
def cancel_membership(member_id):
    member = Member.query.get(member_id)
    if not member:
        flash("Member not found", category="danger")
        return redirect(url_for('members_bp.members_page'))

    # Check if membership is active
    if member.membership_status != 'active':
        flash('Membership is not active', category='danger')
        return redirect(url_for('members_bp.members_page'))

    # Use 20.0 if membership_fee is None
    fee_per_month = member.membership_fee if member.membership_fee is not None else 20.0

    # Calculate total membership duration in days
    total_days = (member.membership_expiry - member.membership_start).days
    if total_days <= 0:  # Prevent division by zero
        flash("Invalid membership duration", category='danger')
        return redirect(url_for('members_bp.members_page'))

    # Calculate used days
    used_days = (datetime.utcnow() - member.membership_start).days
    unused_days = max(0, total_days - used_days)  # Ensure non-negative

    # Calculate total fee paid (approximate months)
    total_months = total_days / 30.0
    total_fee = total_months * fee_per_month

    # Calculate refund (50% of unused portion)
    refund = (unused_days / total_days) * total_fee * 0.5

    # Update membership status
    member.membership_status = 'cancelled'
    member.cancellation_date = datetime.utcnow()
    member.refund_amount = refund

    # Record transaction
    transaction = Transaction(
        member_name=member.member_name,
        type_of_transaction="refund",
        amount=-refund,
        date=date.today(),
        member_id=member.id
    )

    db.session.add(transaction)
    db.session.commit()

    flash(f"Membership cancelled. Refunded ${refund:.2f}", category='success')
    return redirect(url_for('members_bp.members_page'))