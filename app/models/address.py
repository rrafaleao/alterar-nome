from config.database import db
from datetime import datetime
from app.models.utils import uuid4_str

class Address(db.Model):
    __tablename__ = "addresses"

    id = db.Column(db.String(36), primary_key=True, default=uuid4_str)
    user_id = db.Column(db.String(36), db.ForeignKey("store_customers.id", ondelete="CASCADE"))
    cep = db.Column(db.String(10))
    street = db.Column(db.String(255))
    number = db.Column(db.String(20))
    complement = db.Column(db.String(255))
    neighborhood = db.Column(db.String(255))
    city = db.Column(db.String(255))
    state = db.Column(db.String(2))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'cep': self.cep,
            'street': self.street,
            'number': self.number,
            'complement': self.complement,
            'neighborhood': self.neighborhood,
            'city': self.city,
            'state': self.state
        }
