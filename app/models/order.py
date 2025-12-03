from app import db
from datetime import datetime
from app.models.utils import uuid4_str

class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.String(36), primary_key=True, default=uuid4_str)
    store_id = db.Column(db.String(36), db.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="SET NULL"))
    total_amount = db.Column(db.Numeric(12, 2), nullable=False)
    status = db.Column(db.Enum(
        "pending","paid","shipped","delivered","cancelled","refunded",
        name="order_status"
    ), default="pending", nullable=False)
    shipping_address_id = db.Column(db.String(36), db.ForeignKey("addresses.id"))
    placed_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata = db.Column(db.JSON)

    items = db.relationship("OrderItem", backref="order", cascade="all, delete-orphan")
    payment = db.relationship("Payment", backref="order", uselist=False, cascade="all, delete-orphan")

class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.String(36), primary_key=True, default=uuid4_str)
    order_id = db.Column(db.String(36), db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_id = db.Column(db.String(36), db.ForeignKey("products.id", ondelete="SET NULL"))
    title = db.Column(db.String(255), nullable=False)
    sku = db.Column(db.String(255))
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    # MySQL generated column
    # SQLAlchemy does not compute this automatically
    # but we represent it so ORM knows it exists
    total_price = db.Column(db.Numeric(12, 2), nullable=True)
