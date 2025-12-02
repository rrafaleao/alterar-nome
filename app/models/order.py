from datetime import datetime
from config.database import db

class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.String, primary_key=True)
    store_id = db.Column(db.String, db.ForeignKey("stores.id"))
    user_id = db.Column(db.String, db.ForeignKey("users.id"))
    total_amount = db.Column(db.Numeric(12, 2), nullable=False)
    status = db.Column(db.Enum(
        "pending","paid","shipped","delivered","cancelled","refunded",
        name="order_status"
    ), default="pending")
    shipping_address_id = db.Column(db.String, db.ForeignKey("addresses.id"))
    placed_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    metadata = db.Column(db.JSON)

    store = db.relationship("Store", back_populates="orders")
    user = db.relationship("User", back_populates="orders")
    address = db.relationship("Address")
    items = db.relationship("OrderItem", back_populates="order")
    payment = db.relationship("Payment", back_populates="order", uselist=False)


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.String, primary_key=True)
    order_id = db.Column(db.String, db.ForeignKey("orders.id"))
    product_id = db.Column(db.String, db.ForeignKey("products.id"))
    title = db.Column(db.String, nullable=False)
    sku = db.Column(db.String)
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Numeric(12, 2))

    order = db.relationship("Order", back_populates="items")
    product = db.relationship("Product", back_populates="order_items")
