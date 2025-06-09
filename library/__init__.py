from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
import os
from flask_wtf.csrf import CSRFProtect

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
migrate = Migrate(app, db)
csrf = CSRFProtect(app)

login_manager = LoginManager()
login_manager.init_app(app)

from library.models import User, Member


@login_manager.user_loader
def load_user(user_id):
    user = User.query.get(int(user_id))
    if user:
        return user

    member = Member.query.get(int(user_id))
    if member:
        return member

    return None

@login_manager.unauthorized_handler
def unauthorized():
    return redirect(url_for('routes_bp.welcome'))

# Import blueprints
from library.routes.book_routes import book_bp
from library.routes.routes import routes_bp
from library.routes.member_routes import members_bp
from library.routes.transaction_routes import transactions_bp
from library.routes.login_routes import login_bp
from library.routes.client_routes import client

# Register blueprints
app.register_blueprint(book_bp)
app.register_blueprint(routes_bp)
app.register_blueprint(members_bp)
app.register_blueprint(transactions_bp)
app.register_blueprint(login_bp)
app.register_blueprint(client, url_prefix='/client')

# Add root redirect AFTER blueprint registration
@app.route('/')
def root_redirect():
    return redirect(url_for('routes_bp.home_page'))

if __name__ == '__main__':
    app.run(debug=True)