from config.database import db
from datetime import datetime
from app.models.utils import uuid4_str

class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.String(36), primary_key=True, default=uuid4_str)
    order_id = db.Column(db.String(36), db.ForeignKey("orders.id", ondelete="CASCADE"), unique=True)
    method = db.Column(db.String(255))
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    status = db.Column(db.Enum(
        "created","authorized","captured","failed","refunded",
        name="payment_status"
    ), default="created")
    payment_data = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
