from flask import Flask
from app.config import Config
from app.extensions import db, login_manager, migrate
import markdown

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.jinja_env.globals.update(hasattr=hasattr)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app)
    @app.template_filter('render_markdown')
    def render_markdown_filter(text):
        if not text:
            return ""
        return markdown.markdown(text, extensions=['extra'])

    # Register Blueprints
    from app.auth.routes import auth_bp
    from app.dashboard.routes import dashboard_bp
    from app.loans.routes import loans_bp
    from app.community.routes import community_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/')
    app.register_blueprint(loans_bp, url_prefix='/loans')
    app.register_blueprint(community_bp, url_prefix='/community')

    return app