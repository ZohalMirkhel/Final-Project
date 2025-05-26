import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
ENV = 'dev'

if ENV == 'dev':
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
    app.config['SECRET_KEY'] = '7449cd3db56ab9b3645b5a81deb0a3b4ec0e685c502540ee'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['SQL_DATABASE_URL']
    app.config['SECRET_KEY'] = os.environ['SECRET_KEY']

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ✅ Import your blueprints here
from library.routes.book_routes import book_bp
from library.routes.routes import routes_bp
from library.routes.member_routes import members_bp
from library.routes.transaction_routes import transactions_bp

# ✅ Register blueprints
app.register_blueprint(book_bp)
app.register_blueprint(routes_bp)
app.register_blueprint(members_bp)
app.register_blueprint(transactions_bp)

if __name__ == '__main__':
    app.run(debug=True)
