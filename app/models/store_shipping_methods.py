from config.database import db
from datetime import datetime

class StoreShippingMethod(db.Model):
    __tablename__ = 'store_shipping_methods'
    
    id = db.Column(db.String(36), primary_key=True)
    store_id = db.Column(db.String(36), db.ForeignKey('stores.id', ondelete='CASCADE'), nullable=False)
    method = db.Column(db.Enum('correios', 'fixed', 'pickup', 'custom'), nullable=False)
    is_enabled = db.Column(db.Boolean, nullable=False, default=True)
    config = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamento
    store = db.relationship('Store', back_populates='shipping_methods')
    
    __table_args__ = (
        db.UniqueConstraint('store_id', 'method', name='unique_store_shipping_method'),
    )
    
    def __repr__(self):
        return f'<StoreShippingMethod {self.method} for store {self.store_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'store_id': self.store_id,
            'method': self.method,
            'is_enabled': self.is_enabled,
            'config': self.config,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }