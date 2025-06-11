import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytest
from datetime import datetime, timedelta, date
from werkzeug.security import generate_password_hash, check_password_hash
from library import create_app, db
from library.models import (
    User, Member, Book, Transaction, Book_borrowed, Checkout,
    Feedback, Cart, ReturnRequest
)
from library.forms import (
    RegistrationForm, LoginForm, member_form, book_form,
    MembershipForm, ChangePasswordForm, PaymentForm
)
import re


# Fixtures for testing
@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['WTF_CSRF_CHECK_DEFAULT'] = True

    with app.app_context():
        db.create_all()

        # Create test admin user
        admin = User(
            name="Admin User",
            email="admin@test.com",
            phone="1234567890",
            password=generate_password_hash("adminpass"),
            address="123 Admin St",
            role="admin"
        )
        db.session.add(admin)

        # Create test regular user
        regular_user = User(
            name="Test User",
            email="user@test.com",
            phone="0987654321",
            password=generate_password_hash("userpass"),
            address="456 User Ave",
            role="customer"
        )
        db.session.add(regular_user)
        db.session.commit()

        # Create test member
        member = Member(
            name="Test Member",
            member_name="testmember",
            phone_number="1112223333",
            membership_status="active",
            membership_start=datetime.utcnow(),
            membership_expiry=datetime.utcnow() + timedelta(days=30),
            user_id=regular_user.id
        )
        db.session.add(member)

        # Create test book
        book = Book(
            title="Test Book",
            isbn="1234567890123",
            author="Test Author",
            category="Test",
            stock=5,
            borrow_stock=3,
            price=19.99
        )
        db.session.add(book)
        db.session.commit()

        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


# Model Tests
def test_user_model(app):
    with app.app_context():
        user = User.query.filter_by(email="user@test.com").first()
        assert user is not None
        assert user.name == "Test User"
        assert check_password_hash(user.password, "userpass")
        assert not user.is_member()
        assert not user.is_active_member()


def test_member_model(app):
    with app.app_context():
        member = Member.query.filter_by(member_name="testmember").first()
        assert member is not None
        assert member.name == "Test Member"
        assert member.is_active_member()
        assert member.get_id() == str(member.id)

        # Test membership expiration
        user = User.query.filter_by(email="user@test.com").first()
        expired_member = Member(
            name="Expired Member",
            member_name="expired",
            phone_number="4445556666",
            membership_status="active",
            membership_start=datetime.utcnow() - timedelta(days=60),
            membership_expiry=datetime.utcnow() - timedelta(days=30),
            user_id=user.id
        )
        db.session.add(expired_member)
        db.session.commit()
        assert not expired_member.is_active_member()


def test_book_model(app):
    with app.app_context():
        book = Book.query.filter_by(title="Test Book").first()
        assert book is not None
        assert book.author == "Test Author"
        assert book.available is True
        book.stock = 0
        db.session.commit()
        assert book.stock == 0

def test_transaction_model(app):
    with app.app_context():
        member = Member.query.first()
        book = Book.query.first()

        transaction = Transaction(
            book_name=book.title,
            member_name=member.member_name,
            type_of_transaction="sale",
            amount=book.price,
            date=date.today(),
            book_id=book.id,
            member_id=member.id
        )
        db.session.add(transaction)
        db.session.commit()

        assert transaction.id is not None
        assert transaction.amount == 19.99


def test_checkout_model(app):
    with app.app_context():
        member = Member.query.first()
        book = Book.query.first()

        checkout = Checkout(
            member_id=member.id,
            book_id=book.id,
            checkout_date=datetime.utcnow(),
            due_date=datetime.utcnow() + timedelta(days=14)
        )
        db.session.add(checkout)
        db.session.commit()

        assert checkout.id is not None
        assert checkout.return_date is None


# Form Tests
def test_registration_form_valid(app):
    with app.app_context():
        form = RegistrationForm(
            name="New User",
            email="new@test.com",
            phone="5556667777",
            password="ValidPass123!",
            address="123 Test St",
            role="customer"
        )
        form.confirm_password = "ValidPass123!"
        assert form.validate() is True


def test_registration_form_invalid(app):
    with app.app_context():
        form = RegistrationForm(
            name="New User",
            email="user@test.com",
            phone="5556667777",
            password="ValidPass123!",
            address="123 Test St",
            role="customer"
        )
        form.confirm_password = "ValidPass123!"
        assert form.validate() is False
        assert "That email is already in use!" in str(form.errors)


def test_login_form_valid(app):
    with app.app_context():
        form = LoginForm(
            email="user@test.com",
            password="userpass",
            remember=False
        )
        assert form.validate() is True


def test_password_complexity():
    assert re.search(r'[!@#$%^&*(),.?":{}|<>]', "Test123!") is not None
    assert len("Test123!") >= 8


# Integration Tests
def test_admin_login(client):
    response = client.post('/admin_login', data={
        'email': 'admin@test.com',
        'password': 'adminpass'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Admin logged in successfully" in response.data


def test_client_login(client):
    response = client.post('/client_login', data={
        'email': 'user@test.com',
        'password': 'userpass'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Logged in successfully" in response.data


def test_add_book(client):
    client.post('/admin_login', data={
        'email': 'admin@test.com',
        'password': 'adminpass'
    }, follow_redirects=True)

    response = client.post('/books', data={
        'title': 'Added Book',
        'isbn': '1112223334445',
        'author': 'Added Author',
        'category': 'Science',
        'price': '39.99',
        'stock': '5',
        'submit': 'Submit'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Successfully created a book" in response.data


def test_borrow_book(client, app):
    with app.app_context():
        # Login as admin
        client.post('/admin_login', data={
            'email': 'admin@test.com',
            'password': 'adminpass'
        }, follow_redirects=True)

        member = Member.query.first()
        book = Book.query.first()

        response = client.post('/borrow-book', data={
            'member_name': str(member.id),
            'book_name': str(book.id),
            'borrow_fee': '0'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b"Book borrowed successfully" in response.data


def test_return_book(client, app):
    with app.app_context():
        # First borrow a book
        member = Member.query.first()
        book = Book.query.first()

        borrow = Book_borrowed(
            book_id=book.id,
            member_id=member.id,
            borrowed_date=datetime.utcnow(),
            due_date=datetime.utcnow() + timedelta(days=14)
        )
        db.session.add(borrow)
        db.session.commit()

        # Login as admin
        client.post('/admin_login', data={
            'email': 'admin@test.com',
            'password': 'adminpass'
        }, follow_redirects=True)

        response = client.post('/return-book', data={
            'member_name': str(member.id),
            'book_name': str(book.id)
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b"Book returned successfully" in response.data



def test_client_borrow_flow(client, app):
    def test_client_borrow_flow(client, app):
        with app.app_context():
            user = User.query.filter_by(email="user@test.com").first()
            member = Member(
                name="Test Member",
                member_name="testmember2",
                phone_number="1112224444",
                membership_status="active",
                membership_start=datetime.utcnow(),
                membership_expiry=datetime.utcnow() + timedelta(days=30),
                user_id=user.id
            )
            db.session.add(member)
            db.session.commit()

        client.post('/client_login', data={
            'email': 'user@test.com',
            'password': 'userpass'
        }, follow_redirects=True)

        book = Book.query.first()
        book.borrow_stock = 5
        book.available = True
        db.session.commit()

        response = client.post(f'/add-to-cart/{book.id}', data={
            'action': 'borrow',
            'csrf_token': 'fake-csrf-token'
        }, follow_redirects=True)
        print(response.data)
        assert response.status_code == 200
        assert b"Added to cart" in response.data


def test_membership_purchase(client, app):
    with app.app_context():
        # Login as client
        client.post('/client_login', data={
            'email': 'user@test.com',
            'password': 'userpass'
        }, follow_redirects=True)

        response = client.post('/client/buy-membership', data={
            'months': '3',
            'cardholder_name': 'Test User',
            'card_number': '4111111111111111',
            'expiry_date': '12/25',
            'cvv': '123'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b"Membership purchased successfully" in response.data


# Edge Case Tests
def test_borrow_limit(client, app):
    with app.app_context():
        # Login as admin
        client.post('/admin_login', data={
            'email': 'admin@test.com',
            'password': 'adminpass'
        }, follow_redirects=True)

        member = Member.query.first()
        book = Book.query.first()

        # Create 10 borrow records
        for i in range(10):
            borrow = Book_borrowed(
                book_id=book.id,
                member_id=member.id,
                borrowed_date=datetime.utcnow(),
                due_date=datetime.utcnow() + timedelta(days=14))
            db.session.add(borrow)
        db.session.commit()

        # Try to borrow one more
        response = client.post('/borrow-book', data={
            'member_name': str(member.id),
            'book_name': str(book.id),
            'borrow_fee': '0'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b"maximum limit of 10 borrowed books" in response.data


def test_late_return(client, app):
    with app.app_context():
        # Login as admin
        client.post('/admin_login', data={
            'email': 'admin@test.com',
            'password': 'adminpass'
        }, follow_redirects=True)

        member = Member.query.first()
        book = Book.query.first()

        # Create borrow record with past due date
        borrow = Book_borrowed(
            book_id=book.id,
            member_id=member.id,
            borrowed_date=datetime.utcnow() - timedelta(days=21),
            due_date=datetime.utcnow() - timedelta(days=7))
        db.session.add(borrow)
        db.session.commit()

        # Return the book
        response = client.post('/return-book', data={
            'member_name': str(member.id),
            'book_name': str(book.id)
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b"late fee" in response.data


# Security Tests
def test_csrf_protection(app, client):
    # Login as admin
    client.post('/admin_login', data={
        'email': 'admin@test.com',
        'password': 'adminpass'
    }, follow_redirects=True)

    # Try to post without CSRF token (should fail)
    app.config['WTF_CSRF_ENABLED'] = True
    with app.app_context():
        book = Book.query.first()

    response = client.post('/books', data={
        'title': 'CSRF Test Book',
        'isbn': '9998887776665',
        'author': 'CSRF Author',
        'category': 'Test',
        'price': '9.99',
        'stock': '1'
    }, follow_redirects=True)

    assert response.status_code == 400
    assert b"CSRF token is missing" in response.data


def test_sql_injection_attempt(client):
    response = client.post('/client_login', data={
        'email': "' OR '1'='1",
        'password': "' OR '1'='1"
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"login" in response.data.lower() or b"sign in" in response.data.lower()