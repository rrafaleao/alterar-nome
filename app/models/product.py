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
    size_guide_json = db.Column(db.JSON)
    active = db.Column(db.Boolean, default=True)
    show_in_zappshop = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    images = db.relationship("ProductImage", backref="product", cascade="all, delete-orphan")
    stock = db.relationship("ProductStock", backref="product", uselist=False, cascade="all, delete-orphan")
    size_stocks = db.relationship("ProductSizeStock", backref="product", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'store_id': self.store_id,
            'category_id': self.category_id,
            'title': self.title,
            'description': self.description,
            'sku': self.sku,
            'price': float(self.price) if self.price else 0,
            'size_guide': self.size_guide_json or [],
            'active': self.active,
            'show_in_zappshop': self.show_in_zappshop,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'images': [img.to_dict() for img in self.images] if self.images else [],
            'size_stocks': [ss.to_dict() for ss in self.size_stocks] if self.size_stocks else []
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


class ProductSizeStock(db.Model):
    __tablename__ = "product_size_stocks"

    id = db.Column(db.String(36), primary_key=True, default=uuid4_str)
    product_id = db.Column(db.String(36), db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    size = db.Column(db.String(10), nullable=False)
    quantity = db.Column(db.Integer, default=0, nullable=False)
    reserved_quantity = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("product_id", "size"),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'size': self.size,
            'quantity': self.quantity,
            'reserved_quantity': self.reserved_quantity,
            'available': self.quantity - self.reserved_quantity
        }
