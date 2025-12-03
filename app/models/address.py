from datetime import datetime
from config.database import db

class Address(db.Model):
    __tablename__ = "addresses"

    id = db.Column(db.String, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey("users.id"))
    line1 = db.Column(db.String)
    line2 = db.Column(db.String)
    city = db.Column(db.String)
    state = db.Column(db.String)
    postal_code = db.Column(db.String)
    country = db.Column(db.String)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="addresses")
