from datetime import datetime
from config.database import db

class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.String, primary_key=True)
    store_id = db.Column(db.String, db.ForeignKey("stores.id"))
    category_id = db.Column(db.String, db.ForeignKey("categories.id"))
    title = db.Column(db.String, nullable=False)
    description = db.Column(db.Text)
    sku = db.Column(db.String)
    price = db.Column(db.Numeric(12, 2), nullable=False)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    store = db.relationship("Store", back_populates="products")
    category = db.relationship("Category", back_populates="products")
    images = db.relationship("ProductImage", back_populates="product")
    stock = db.relationship("ProductStock", back_populates="product", uselist=False)
    order_items = db.relationship("OrderItem", back_populates="product")


class ProductImage(db.Model):
    __tablename__ = "product_images"

    id = db.Column(db.String, primary_key=True)
    product_id = db.Column(db.String, db.ForeignKey("products.id"))
    url = db.Column(db.String, nullable=False)
    position = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship("Product", back_populates="images")


class ProductStock(db.Model):
    __tablename__ = "product_stocks"

    product_id = db.Column(db.String, db.ForeignKey("products.id"), primary_key=True)
    quantity = db.Column(db.Integer, default=0)
    reserved_quantity = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship("Product", back_populates="stock")
