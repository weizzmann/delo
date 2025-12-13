import os
from flask import Flask, redirect, url_for
from .config import Config
from .extensions import db, login_manager


def create_app():
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.unauthorized_handler
    def unauthorized():
        return redirect(url_for('auth.login'))

    # Blueprints
    from .auth.routes import auth_bp
    from .main.routes import main_bp
    from .api.documents import api_documents
    from .api.cases import api_cases
    from .api.volumes import api_volumes
    from .api.export import api_export

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)
    app.register_blueprint(api_documents, url_prefix='/api')
    app.register_blueprint(api_cases, url_prefix='/api')
    app.register_blueprint(api_volumes, url_prefix='/api')
    app.register_blueprint(api_export, url_prefix='/api')

    return app
