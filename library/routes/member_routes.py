from flask import Blueprint
from flask import render_template, redirect, url_for, flash, request

from library import db
from library.forms import AdminCreateMemberForm, member_form, AdminChangePasswordForm, UpdateMemberForm, AdminCreateAdminForm
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import current_user
from library.models import Book, Member, Transaction, User
from datetime import datetime, timedelta, date



members_bp = Blueprint('members_bp', __name__)

# Renders member page
@members_bp.route('/members', methods=['GET', 'POST'])
def members_page():
    admin_form = AdminCreateMemberForm()
    member_form_instance = member_form()
    admin_password_form = AdminChangePasswordForm()
    update_member_form = UpdateMemberForm()
    members = Member.query.filter(
        Member.membership_status != 'cancelled'
    ).order_by('id').all()

    for member in members:
        total_paid = Transaction.query.filter_by(
            member_id=member.id,
            type_of_transaction='membership'
        ).with_entities(db.func.sum(Transaction.amount)).scalar() or 0.0
        member.total_paid = total_paid

    books_to_borrow = Book.query.filter(Book.borrow_stock > 0).all()
    members_can_borrow = Member.query.filter(
        Member.membership_status == 'active',
        Member.membership_expiry > datetime.utcnow()
    ).all()
    books_for_sale = Book.query.filter(Book.stock > 0).all()

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

    if admin_form.validate_on_submit():
        hashed_password = generate_password_hash(admin_form.password.data)
        new_user = User(
            name=admin_form.name.data,
            phone=admin_form.phone.data,
            email=admin_form.email.data,
            password=hashed_password,
            address=admin_form.address.data,
            role='customer'
        )
        db.session.add(new_user)
        db.session.flush()

        # Create Member linked to User
        start_date = datetime.utcnow()
        expiry_date = start_date + timedelta(days=30 * admin_form.membership_months.data)
        new_member = Member(
            name=admin_form.name.data,
            phone_number=admin_form.phone.data,
            member_name=admin_form.member_name.data,
            membership_status='active',
            membership_start=start_date,
            membership_expiry=expiry_date,
            membership_fee=20.0,
            user_id=new_user.id
        )
        db.session.add(new_member)

        transaction = Transaction(
            book_name="Membership Fee",
            member_name=new_member.member_name,
            type_of_transaction="membership",
            amount=admin_form.membership_months.data * 20.0,
            date=date.today(),
            member_id=new_member.id,
            user_id=new_user.id
        )
        db.session.add(transaction)

        db.session.commit()
        flash('Member created successfully!', 'success')
        return redirect(url_for('members_bp.members_page'))

    if admin_form.errors:
        for err_msgs in admin_form.errors.values():
            for err_msg in err_msgs:
                flash(f'Error creating member: {err_msg}', category='danger')

    return render_template('members/members.html',
                           admin_form=AdminCreateMemberForm(),
                           update_member_form=update_member_form,
                           admin_password_form=admin_password_form,
                           member_form=member_form_instance,
                           members=members,
                           length=len(members),
                           books_to_borrow=books_to_borrow,
                           members_can_borrow=members_can_borrow,
                           books_to_return=books_to_return,
                           books_for_sale=books_for_sale,
                           current_date=datetime.utcnow().date())


# updates a member
@members_bp.route('/update-member/<member_id>', methods=['GET', 'POST'])
def update_member(member_id):
    member = Member.query.filter_by(id=member_id).first()
    user = User.query.get(member.user_id)

    newName = request.form.get("name")
    newNumber = request.form.get("phone_number")
    newMember = request.form.get("member_name")
    newEmail = request.form.get("email")

    try:
        # Validate email uniqueness
        if newEmail != user.email:
            existing_user = User.query.filter(User.email == newEmail, User.id != user.id).first()
            if existing_user:
                flash("Email already in use by another user", category="danger")
                return redirect(url_for('members_bp.members_page'))

        # Update member fields
        if member.name != newName:
            member.name = newName
        if member.phone_number != newNumber:
            member.phone_number = newNumber
        if member.member_name != newMember:
            member.member_name = newMember

        # Update user email
        if user.email != newEmail:
            user.email = newEmail

        db.session.commit()
        flash("Updated Successfully!", category="success")

    except Exception as e:
        flash(f"Failed to update: {str(e)}", category="danger")

    return redirect(url_for('members_bp.members_page'))


@members_bp.route('/renew-membership/<member_id>', methods=['POST'])
def renew_membership(member_id):
    member = Member.query.get(member_id)
    if not member:
        flash("Member not found", category="danger")
        return redirect(url_for('members_bp.members_page'))

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
    if total_days <= 0:
        flash("Invalid membership duration", category='danger')
        return redirect(url_for('members_bp.members_page'))

    # Calculate used days
    used_days = (datetime.utcnow() - member.membership_start).days
    unused_days = max(0, total_days - used_days)

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


@members_bp.route('/update-member-password/<int:member_id>', methods=['POST'])
def update_member_password(member_id):
    member = Member.query.get(member_id)
    if not member:
        flash("Member not found", category="danger")
        return redirect(url_for('members_bp.members_page'))

    form = AdminChangePasswordForm()
    if form.validate_on_submit():
        user = User.query.get(member.user_id)
        if user:
            # Additional validation
            if len(form.new_password.data) < 8:
                flash("Password must be at least 8 characters", category="danger")
                return redirect(url_for('members_bp.members_page'))

            if not any(char in '!@#$%^&*(),.?":{}|<>' for char in form.new_password.data):
                flash("Password must contain at least one special character", category="danger")
                return redirect(url_for('members_bp.members_page'))

            user.password = generate_password_hash(form.new_password.data)
            db.session.commit()
            flash("Password updated successfully!", category="success")
        else:
            flash("User account not found", category="danger")
    else:
        for error in form.errors.values():
            flash(f"Error: {error[0]}", category="danger")

    return redirect(url_for('members_bp.members_page'))

# Add to members_routes.py

# Admin management page
@members_bp.route('/admins')
def admins_page():
    admins = User.query.filter_by(role='admin').all()
    admin_form = AdminCreateAdminForm()
    return render_template('members/admins.html',
                         admins=admins,
                         admin_form=admin_form)

# Create admin
@members_bp.route('/create-admin', methods=['POST'])
def create_admin():
    form = AdminCreateAdminForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        new_admin = User(
            name=form.name.data,
            phone=form.phone.data,
            email=form.email.data,
            password=hashed_password,
            address=form.address.data,
            role='admin'
        )
        db.session.add(new_admin)
        db.session.commit()
        flash('Admin created successfully!', 'success')
    else:
        for err_msgs in form.errors.values():
            for err_msg in err_msgs:
                flash(f'Error creating admin: {err_msg}', category='danger')
    return redirect(url_for('members_bp.admins_page'))

# Update admin
@members_bp.route('/update-admin/<int:admin_id>', methods=['POST'])
def update_admin(admin_id):
    admin = User.query.get(admin_id)
    if not admin or admin.role != 'admin':
        flash("Admin not found", category="danger")
        return redirect(url_for('members_bp.admins_page'))

    new_name = request.form.get("name")
    new_phone = request.form.get("phone")
    new_email = request.form.get("email")
    new_address = request.form.get("address")

    try:
        # Validate email uniqueness
        if new_email != admin.email:
            existing_user = User.query.filter(User.email == new_email, User.id != admin.id).first()
            if existing_user:
                flash("Email already in use by another user", category="danger")
                return redirect(url_for('members_bp.admins_page'))

        # Validate phone uniqueness
        if new_phone != admin.phone:
            existing_user = User.query.filter(User.phone == new_phone, User.id != admin.id).first()
            if existing_user:
                flash("Phone number already in use by another user", category="danger")
                return redirect(url_for('members_bp.admins_page'))

        # Update admin fields
        admin.name = new_name
        admin.phone = new_phone
        admin.email = new_email
        admin.address = new_address

        db.session.commit()
        flash("Admin updated successfully!", category="success")

    except Exception as e:
        flash(f"Failed to update admin: {str(e)}", category="danger")

    return redirect(url_for('members_bp.admins_page'))

# Delete admin
@members_bp.route('/delete-admin/<int:admin_id>', methods=['POST'])
def delete_admin(admin_id):
    if current_user.id == admin_id:
        flash("You cannot delete your own account!", category="danger")
        return redirect(url_for('members_bp.admins_page'))

    admin = User.query.get(admin_id)
    if not admin or admin.role != 'admin':
        flash("Admin not found", category="danger")
        return redirect(url_for('members_bp.admins_page'))

    try:
        db.session.delete(admin)
        db.session.commit()
        flash("Admin deleted successfully!", category="success")
    except Exception as e:
        flash(f"Failed to delete admin: {str(e)}", category="danger")

    return redirect(url_for('members_bp.admins_page'))

# Update admin password
@members_bp.route('/update-admin-password/<int:admin_id>', methods=['POST'])
def update_admin_password(admin_id):
    admin = User.query.get(admin_id)
    if not admin or admin.role != 'admin':
        flash("Admin not found", category="danger")
        return redirect(url_for('members_bp.admins_page'))

    form = AdminChangePasswordForm()
    if form.validate_on_submit():
        # Additional validation
        if len(form.new_password.data) < 8:
            flash("Password must be at least 8 characters", category="danger")
            return redirect(url_for('members_bp.admins_page'))

        if not any(char in '!@#$%^&*(),.?":{}|<>' for char in form.new_password.data):
            flash("Password must contain at least one special character", category="danger")
            return redirect(url_for('members_bp.admins_page'))

        admin.password = generate_password_hash(form.new_password.data)
        db.session.commit()
        flash("Password updated successfully!", category="success")
    else:
        for error in form.errors.values():
            flash(f"Error: {error[0]}", category="danger")

    return redirect(url_for('members_bp.admins_page'))