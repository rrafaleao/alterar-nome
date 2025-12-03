from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app.routes.init import all_blueprints
from config.database import db


def create_app():
    app = Flask(__name__)

    # -----------------------------------------
    # CONFIGURAÇÕES BÁSICAS DO SISTEMA
    # -----------------------------------------
    app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:@localhost:3306/sem_nome_ainda"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = "uma-chave-secreta-muito-segura"
    db.init_app(app)

    for bp in all_blueprints:
        app.register_blueprint(bp)

    return app
