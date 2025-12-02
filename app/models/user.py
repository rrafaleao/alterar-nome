from datetime import datetime
from config.database import db

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.String, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=False)
    password_hash = db.Column(db.String, nullable=False)
    full_name = db.Column(db.String)
    is_active = db.Column(db.Boolean, default=True)
    is_seller = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    stores = db.relationship("Store", back_populates="owner")
    addresses = db.relationship("Address", back_populates="user")
    carts = db.relationship("Cart", back_populates="user")
    orders = db.relationship("Order", back_populates="user")
