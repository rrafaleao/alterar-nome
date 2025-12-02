from datetime import datetime
from config.database import db

class Cart(db.Model):
    __tablename__ = "carts"

    id = db.Column(db.String, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="carts")
    items = db.relationship("CartItem", back_populates="cart")


class CartItem(db.Model):
    __tablename__ = "cart_items"

    id = db.Column(db.String, primary_key=True)
    cart_id = db.Column(db.String, db.ForeignKey("carts.id"))
    product_id = db.Column(db.String, db.ForeignKey("products.id"))
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    cart = db.relationship("Cart", back_populates="items")
    product = db.relationship("Product")
