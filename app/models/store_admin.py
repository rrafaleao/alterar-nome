from config.database import db
from datetime import datetime
from app.models.utils import uuid4_str


class StoreAdmin(db.Model):
    __tablename__ = 'store_admins'

    id = db.Column(db.String(36), primary_key=True, default=uuid4_str)
    store_id = db.Column(db.String(36), db.ForeignKey('stores.id', ondelete='CASCADE'), nullable=False)
    customer_id = db.Column(db.String(36), db.ForeignKey('store_customers.id', ondelete='CASCADE'), nullable=False)
    role = db.Column(db.Enum('owner', 'admin'), nullable=False, default='admin')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    store = db.relationship('Store', backref=db.backref('admins', lazy='dynamic'))
    customer = db.relationship('StoreCustomer', backref=db.backref('admin_stores', lazy='dynamic'))

    __table_args__ = (
        db.UniqueConstraint('store_id', 'customer_id', name='unique_store_admin'),
        db.Index('idx_store_admins_store', 'store_id'),
        db.Index('idx_store_admins_customer', 'customer_id'),
    )

    def __repr__(self):
        return f'<StoreAdmin {self.customer_id} @ store {self.store_id} ({self.role})>'

    def to_dict(self):
        return {
            'id': self.id,
            'store_id': self.store_id,
            'customer_id': self.customer_id,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @staticmethod
    def is_admin(store_id, customer_id):
        """Verifica se um customer é admin da loja"""
        if not store_id or not customer_id:
            return False
        admin = StoreAdmin.query.filter_by(store_id=store_id, customer_id=customer_id).first()
        return admin is not None
    
    @staticmethod
    def is_owner(store_id, customer_id):
        """Verifica se um customer é owner da loja"""
        if not store_id or not customer_id:
            return False
        admin = StoreAdmin.query.filter_by(store_id=store_id, customer_id=customer_id, role='owner').first()
        return admin is not None
    
    @staticmethod
    def get_admin_role(store_id, customer_id):
        """Retorna a role do admin ou None se não for admin"""
        if not store_id or not customer_id:
            return None
        admin = StoreAdmin.query.filter_by(store_id=store_id, customer_id=customer_id).first()
        return admin.role if admin else None
