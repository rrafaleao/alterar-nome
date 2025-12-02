from datetime import datetime
from config.database import db

class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.String, primary_key=True)
    order_id = db.Column(db.String, db.ForeignKey("orders.id"), unique=True)
    method = db.Column(db.String)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    status = db.Column(db.Enum(
        "created","authorized","captured","failed","refunded",
        name="payment_status"
    ), default="created")
    payment_data = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    order = db.relationship("Order", back_populates="payment")
