from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
import os
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail

# Initialize extensions without app first
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
mail = Mail()

def create_app():
    app = Flask(__name__)
    ENV = 'dev'

    if ENV == 'dev':
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'library.db')
        app.config['SECRET_KEY'] = 'your-secret-key'
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['SQL_DATABASE_URL']
        app.config['SECRET_KEY'] = os.environ['SECRET_KEY']

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'zohalmirkhel@gmail.com'
    app.config['MAIL_PASSWORD'] = 'kzeg knrt vmhf daad'
    app.config['MAIL_DEFAULT_SENDER'] = 'zohalmirkhel@gmail.com'

    mail.init_app(app)
    from library.models import User, Member

    @login_manager.user_loader
    def load_user(user_id):
        user = User.query.get(int(user_id))
        if user:
            return user
        member = Member.query.get(int(user_id))
        return member if member else None

    @login_manager.unauthorized_handler
    def unauthorized():
        return redirect(url_for('routes_bp.welcome'))

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

    @app.route('/')
    def root_redirect():
        return redirect(url_for('routes_bp.home_page'))

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)