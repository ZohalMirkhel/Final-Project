from flask import Blueprint, session, request, redirect, url_for, flash, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from library.models import User, db
from flask_login import login_user, logout_user, login_required, current_user
from library.forms import LoginForm, RegistrationForm

# Create the blueprint
# client_bp = Blueprint('client', __name__, url_prefix='/client')
login_bp = Blueprint('login_bp', __name__)


@login_bp.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        # Find admin user
        user = User.query.filter_by(email=email, role='admin').first()

        if user:
            if check_password_hash(user.password, password):
                login_user(user)
                flash('Admin logged in successfully!', 'success')
                return redirect(url_for('routes_bp.home_page'))
            else:
                flash('Incorrect password', 'error')
        else:
            flash('Admin account not found', 'error')

    return render_template('admin_login.html', form=form)


@login_bp.route('/client_login', methods=['GET', 'POST'])
def client_login():
    form = LoginForm()

    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user = User.query.filter_by(email=email).first()

        if user:
            # Check if the user is an admin
            if user.role == 'admin':
                flash('Admin accounts cannot log in to client side', 'error')
                return render_template('client_login.html', form=form)

            if check_password_hash(user.password, password):
                login_user(user)
                flash('Logged in successfully!', 'success')
                return redirect(url_for('client.client_home'))
            else:
                flash('Invalid email or password', 'error')
        else:
            flash('Invalid email or password', 'error')

    return render_template('client_login.html', form=form)


@login_bp.route('/register', methods=['GET', 'POST'])
def registration_form():
    form = RegistrationForm()
    if form.validate_on_submit():
        new_user = User(
            name=form.name.data,
            phone=form.phone.data,
            email=form.email.data,
            password=generate_password_hash(form.password.data),
            address=form.address.data,
            role=form.role.data
        )
        try:
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login_bp.client_login'))
        except Exception as e:
            db.session.rollback()
            flash("Registration failed: " + str(e), "error")
    return render_template('registration_form.html', form=form)


@login_bp.route('/admin_logout')
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for('login_bp.admin_login'))

@login_bp.route('/client_logout')
@login_required
def client_logout():
    logout_user()
    return redirect(url_for('login_bp.client_login'))

