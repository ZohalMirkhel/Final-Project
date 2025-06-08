from flask import Blueprint, session, request, redirect, url_for, flash, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from library.models import User, db
from flask_login import login_user
from library.forms import LoginForm
from flask_wtf.csrf import generate_csrf

# Create the blueprint
client_bp = Blueprint('client', __name__, url_prefix='/client')
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
    form = LoginForm()  # Create a form instance

    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('client.client_home'))
        else:
            flash('Invalid email or password', 'error')

    return render_template('client_login.html', form=form)  # Pass form to template



@login_bp.route('/register', methods=['GET', 'POST'])
def registration_form():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        email = request.form['email']
        password = request.form['password']
        address = request.form['address']
        role = request.form['role']

        print(f"[DEBUG] Registering user: {email}, role: {role}")

        try:
            new_user = User(name=name, phone=phone, email=email, password=generate_password_hash(password), address=address, role=role)
            db.session.add(new_user)
            db.session.commit()
            print("[DEBUG] Registration successful")
            return redirect(url_for('login_bp.registration_success'))
        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Registration failed: {str(e)}")
            flash("Registration failed. Possibly due to duplicate email/phone.", "error")

    return render_template('registration_form.html')


@login_bp.route('/registration-success', methods=['GET'])
def registration_success():
    return render_template('registration_success.html')


