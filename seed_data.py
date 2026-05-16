from library import create_app, db
from library.models import User, Member, Book
from datetime import datetime, timedelta

app = create_app()

with app.app_context():
    # Create all tables
    db.create_all()
    
    print("Creating sample data...")
    
    # Create admin user
    user = User(
        name="Admin User",
        phone="1234567890",
        email="admin@library.com",
        password="password123",
        address="123 Library Street, Kabul",
        role="admin",
        created_at=datetime.now()
    )
    db.session.add(user)
    db.session.flush()  # Get the user ID
    
    # Create member user first (for the member relationship)
    member_user = User(
        name="John Doe",
        phone="0789123456",
        email="john@email.com",
        password="password123",
        address="456 Main Road, Kabul",
        role="member",
        created_at=datetime.now()
    )
    db.session.add(member_user)
    db.session.flush()
    
    # Create member profile
    member = Member(
        name="John Doe",
        member_name="johndoe123",
        phone_number="0789123456",
        membership_status="active",
        membership_expiry=datetime.now() + timedelta(days=365),
        membership_start=datetime.now(),
        membership_fee=20.0,
        user_id=member_user.id
    )
    db.session.add(member)
    
    # Create another member
    member2_user = User(
        name="Jane Smith",
        phone="0799123456",
        email="jane@email.com",
        password="password123",
        address="789 Park Avenue, Kabul",
        role="member",
        created_at=datetime.now()
    )
    db.session.add(member2_user)
    db.session.flush()
    
    member2 = Member(
        name="Jane Smith",
        member_name="janesmith456",
        phone_number="0799123456",
        membership_status="active",
        membership_expiry=datetime.now() + timedelta(days=180),
        membership_start=datetime.now(),
        membership_fee=20.0,
        user_id=member2_user.id
    )
    db.session.add(member2)
    
    # Add sample books
    books = [
        Book(
            title="The Great Gatsby",
            isbn="978-0743273565",
            author="F. Scott Fitzgerald",
            category="Fiction",
            stock=5,
            borrow_stock=3,
            price=15.99,
            available=True,
            sales_count=0
        ),
        Book(
            title="1984",
            isbn="978-0451524935",
            author="George Orwell",
            category="Fiction",
            stock=4,
            borrow_stock=2,
            price=12.99,
            available=True,
            sales_count=0
        ),
        Book(
            title="To Kill a Mockingbird",
            isbn="978-0446310789",
            author="Harper Lee",
            category="Fiction",
            stock=3,
            borrow_stock=3,
            price=14.99,
            available=True,
            sales_count=0
        ),
        Book(
            title="Python Programming Basics",
            isbn="978-1234567890",
            author="John Smith",
            category="Education",
            stock=10,
            borrow_stock=5,
            price=29.99,
            available=True,
            sales_count=0
        ),
        Book(
            title="Introduction to Database Systems",
            isbn="978-0987654321",
            author="C.J. Date",
            category="Education",
            stock=6,
            borrow_stock=4,
            price=35.99,
            available=True,
            sales_count=0
        ),
    ]
    
    for book in books:
        db.session.add(book)
    
    # Commit everything
    db.session.commit()
    
    print("=" * 50)
    print("  DATABASE SEEDED SUCCESSFULLY!")
    print("=" * 50)
    print(f"  Users created: 3")
    print(f"  Members created: 2")
    print(f"  Books created: {len(books)}")
    print("=" * 50)
    print("  Login credentials:")
    print("  Admin - Email: admin@library.com")
    print("  Password: password123")
    print("=" * 50)