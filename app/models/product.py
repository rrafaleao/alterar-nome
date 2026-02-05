from config.database import db
from datetime import datetime
from .utils import uuid4_str

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

    def to_dict(self):
        return {
            'id': self.id,
            'store_id': self.store_id,
            'category_id': self.category_id,
            'title': self.title,
            'description': self.description,
            'sku': self.sku,
            'price': float(self.price) if self.price else 0,
            'active': self.active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'images': [img.to_dict() for img in self.images] if self.images else []
        }

class ProductImage(db.Model):
    __tablename__ = "product_images"

    id = db.Column(db.String(36), primary_key=True, default=uuid4_str)
    product_id = db.Column(db.String(36), db.ForeignKey("products.id", ondelete="CASCADE"))
    url = db.Column(db.Text, nullable=False)
    position = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'url': self.url,
            'position': self.position,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class ProductStock(db.Model):
    __tablename__ = "product_stocks"

    product_id = db.Column(db.String(36), db.ForeignKey("products.id", ondelete="CASCADE"),
                           primary_key=True)
    quantity = db.Column(db.Integer, default=0, nullable=False)
    reserved_quantity = db.Column(db.Integer, default=0, nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
