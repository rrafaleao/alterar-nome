from config.database import db
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    full_name = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(15), nullable=True)  # NOVO CAMPO
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_seller = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    stores = db.relationship('Store', back_populates='owner', cascade='all, delete-orphan')
    
    __table_args__ = (
        db.Index('idx_users_email', 'email'),
    )
    
    def __repr__(self):
        return f'<User {self.email}>'
    
    def to_dict(self, include_stores=False):
        data = {
            'id': self.id,
            'email': self.email,
            'full_name': self.full_name,
            'phone': self.phone,
            'is_active': self.is_active,
            'is_seller': self.is_seller,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_stores:
            data['stores'] = [store.to_dict() for store in self.stores]
        
        return data