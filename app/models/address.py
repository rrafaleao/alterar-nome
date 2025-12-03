from app import db
from datetime import datetime
from app.models.utils import uuid4_str

class Address(db.Model):
    __tablename__ = "addresses"

    id = db.Column(db.String(36), primary_key=True, default=uuid4_str)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"))
    line1 = db.Column(db.Text)
    line2 = db.Column(db.Text)
    city = db.Column(db.Text)
    state = db.Column(db.Text)
    postal_code = db.Column(db.Text)
    country = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
