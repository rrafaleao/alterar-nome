from flask import Flask
from config.database import db 
from app.routes import (
    auth_bp,
    user_bp,
    store_bp,
    product_bp,
    cart_bp,
    order_bp
)

def create_app():
    app = Flask(__name__)

    # Config
    app.config.from_object("config.settings")

    # Extensões
    db.init_app(app)

    # Blueprints
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(user_bp, url_prefix="/users")
    app.register_blueprint(store_bp, url_prefix="/stores")
    app.register_blueprint(product_bp, url_prefix="/products")
    app.register_blueprint(cart_bp, url_prefix="/cart")
    app.register_blueprint(order_bp, url_prefix="/orders")

    return app
