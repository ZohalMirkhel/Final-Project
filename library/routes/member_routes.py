# internal imports
from flask import Blueprint
from flask import render_template, redirect, url_for, flash, request

from library import app, db
from library.forms import member_form
from library.models import Book, Member

# external imports


members_bp = Blueprint('members_bp', __name__)

# Renders member page
@members_bp.route('/members', methods=['GET', 'POST'])
def members_page():
    members = Member.query.order_by('id').all()

    form_member = member_form()
    books_to_borrow = Book.query.filter(Book.borrow_stock > 0).all()
    members_can_borrow = Member.query.filter(Member.to_pay < 500).all()
    books_to_return = Book.query.filter(Book.borrower).all()
    books_for_sale = Book.query.filter(Book.stock > 0).all()

    if form_member.validate_on_submit():
        member_to_create = Member(
            name=form_member.name.data,  # FIX: Use actual form instance
            phone_number=form_member.phone_number.data,
            member_name=form_member.member_name.data,
            to_pay=0
        )
        db.session.add(member_to_create)
        db.session.commit()
        flash('Successfully created a member', category="success")
        return redirect(request.referrer)

    if form_member.errors != {}:
        for err_msg in form_member.errors.values():
            flash(f'Error creating member: {err_msg}', category='danger')

    # FIX: Pass 'members' (plural) to template
    return render_template('members/members.html',
                           member_form=form_member,
                           members=members,
                           length=len(members),
                           books_to_borrow=books_to_borrow,
                           members_can_borrow=members_can_borrow,
                           books_to_return=books_to_return,
                           books_for_sale=books_for_sale)

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

    return redirect(url_for('members_page'))
