from app import db
from datetime import datetime
from app.models.utils import uuid4_str

class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.String(36), primary_key=True, default=uuid4_str)
    store_id = db.Column(db.String(36), db.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False)
    category_id = db.Column(db.String(36), db.ForeignKey("categories.id", ondelete="SET NULL"))
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    sku = db.Column(db.String(255))
    price = db.Column(db.Numeric(12, 2), nullable=False)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    images = db.relationship("ProductImage", backref="product", cascade="all, delete-orphan")
    stock = db.relationship("ProductStock", backref="product", uselist=False, cascade="all, delete-orphan")

class ProductImage(db.Model):
    __tablename__ = "product_images"

    id = db.Column(db.String(36), primary_key=True, default=uuid4_str)
    product_id = db.Column(db.String(36), db.ForeignKey("products.id", ondelete="CASCADE"))
    url = db.Column(db.Text, nullable=False)
    position = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ProductStock(db.Model):
    __tablename__ = "product_stocks"

    product_id = db.Column(db.String(36), db.ForeignKey("products.id", ondelete="CASCADE"),
                           primary_key=True)
    quantity = db.Column(db.Integer, default=0, nullable=False)
    reserved_quantity = db.Column(db.Integer, default=0, nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
