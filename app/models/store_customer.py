from config.database import db
from datetime import datetime
from app.models.utils import uuid4_str


class StoreCustomer(db.Model):
    __tablename__ = 'store_customers'

    id = db.Column(db.String(36), primary_key=True, default=uuid4_str)
    store_id = db.Column(db.String(36), db.ForeignKey('stores.id', ondelete='CASCADE'), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    full_name = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(15), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    store = db.relationship('Store', backref=db.backref('customers', lazy='dynamic'))

    __table_args__ = (
        db.UniqueConstraint('store_id', 'email', name='unique_store_customer_email'),
        db.Index('idx_store_customers_store', 'store_id'),
        db.Index('idx_store_customers_email', 'email'),
    )

    def __repr__(self):
        return f'<StoreCustomer {self.email} @ store {self.store_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'store_id': self.store_id,
            'email': self.email,
            'full_name': self.full_name,
            'phone': self.phone,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
