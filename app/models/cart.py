from app import db
from datetime import datetime
from app.models.utils import uuid4_str

class Cart(db.Model):
    __tablename__ = "carts"

    id = db.Column(db.String(36), primary_key=True, default=uuid4_str)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = db.relationship("CartItem", backref="cart", cascade="all, delete-orphan")

class CartItem(db.Model):
    __tablename__ = "cart_items"

    id = db.Column(db.String(36), primary_key=True, default=uuid4_str)
    cart_id = db.Column(db.String(36), db.ForeignKey("carts.id", ondelete="CASCADE"))
    product_id = db.Column(db.String(36), db.ForeignKey("products.id", ondelete="RESTRICT"))
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
