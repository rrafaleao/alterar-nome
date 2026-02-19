from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config.database import db
from app.routes.init import all_blueprints

def create_app():
    app = Flask(__name__)

    # -----------------------------------------
    # CONFIGURAÇÕES BÁSICAS DO SISTEMA
    # -----------------------------------------
    app.config["SQLALCHEMY_DATABASE_URI"] = "mysql://zapp_buffalojoy:2e40b943ffbde6e45c9deb963bec99583e43d8db@vdmz5k.h.filess.io:61002/zapp_buffalojoy"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = "uma-chave-secreta-muito-segura"
    db.init_app(app)

    with app.app_context():
        db.create_all()

    for bp in all_blueprints:
        app.register_blueprint(bp)

    return app
