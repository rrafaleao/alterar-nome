from config.database import db
from datetime import datetime
from app.models.utils import uuid4_str


class CustomerFavorite(db.Model):
    __tablename__ = 'customer_favorites'

    id = db.Column(db.String(36), primary_key=True, default=uuid4_str)
    customer_id = db.Column(db.String(36), db.ForeignKey('store_customers.id', ondelete='CASCADE'), nullable=False)
    product_id = db.Column(db.String(36), db.ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamentos
    customer = db.relationship('StoreCustomer', backref=db.backref('favorites', lazy='dynamic'))
    product = db.relationship('Product', backref=db.backref('favorited_by', lazy='dynamic'))

    __table_args__ = (
        db.UniqueConstraint('customer_id', 'product_id', name='unique_customer_product_favorite'),
        db.Index('idx_customer_favorites_customer', 'customer_id'),
        db.Index('idx_customer_favorites_product', 'product_id'),
    )

    def __repr__(self):
        return f'<CustomerFavorite customer={self.customer_id} product={self.product_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'product_id': self.product_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'product': self.product.to_dict() if self.product else None
        }
