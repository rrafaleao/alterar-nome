from config.database import db
from datetime import datetime
from app.models.utils import uuid4_str

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=uuid4_str)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.Text, nullable=False)
    full_name = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_seller = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    stores = db.relationship("Store", backref="owner", cascade="all, delete-orphan")
    carts = db.relationship("Cart", backref="user")
    addresses = db.relationship("Address", backref="user", cascade="all, delete-orphan")
