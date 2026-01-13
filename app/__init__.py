import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask
from flask_wtf.csrf import CSRFProtect
from config import Config
import db as database

csrf = CSRFProtect()


def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(Config)

    csrf.init_app(app)
    database.init_app(app)

    from app.auth        import bp as auth_bp
    from app.utilisateur import bp as util_bp
    from app.technicien  import bp as tech_bp
    from app.directeur   import bp as dir_bp
    from app.admin       import bp as adm_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(util_bp,  url_prefix='/utilisateur')
    app.register_blueprint(tech_bp,  url_prefix='/technicien')
    app.register_blueprint(dir_bp,   url_prefix='/directeur')
    app.register_blueprint(adm_bp,   url_prefix='/admin')

    return app
