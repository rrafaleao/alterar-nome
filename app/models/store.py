from config.database import db
from datetime import datetime

class Store(db.Model):
    __tablename__ = 'stores'
    
    id = db.Column(db.String(36), primary_key=True)
    owner_id = db.Column(db.String(36), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    slug = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Campos de onboarding
    onboarding_step = db.Column(db.SmallInteger, nullable=False, default=1)
    onboarding_completed = db.Column(db.Boolean, nullable=False, default=False)
    
    # Campos de pessoa física/jurídica
    person_type = db.Column(db.Enum('PF', 'PJ'), nullable=False, default='PF')
    cpf = db.Column(db.String(11), nullable=True)
    cnpj = db.Column(db.String(14), nullable=True)
    legal_name = db.Column(db.String(255), nullable=True)
    
    is_published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    owner = db.relationship('User', back_populates='stores')
    payment_methods = db.relationship('StorePaymentMethod', back_populates='store', cascade='all, delete-orphan')
    shipping_methods = db.relationship('StoreShippingMethod', back_populates='store', cascade='all, delete-orphan')
    
    # ⚠️ IMPORTANTE: Relacionamento com StoreCustomization
    # Como as duas classes estão no mesmo arquivo, use back_populates
    customization = db.relationship(
        'StoreCustomization', 
        back_populates='store',  # Deve corresponder ao atributo em StoreCustomization
        uselist=False,  # Relacionamento um-para-um
        cascade='all, delete-orphan'
    )
    
    __table_args__ = (
        db.UniqueConstraint('owner_id', 'slug', name='unique_owner_slug'),
        db.Index('idx_stores_slug', 'slug'),
    )
    
    def __repr__(self):
        return f'<Store {self.name} ({self.slug})>'
    
    def to_dict(self, include_details=False):
        data = {
            'id': self.id,
            'owner_id': self.owner_id,
            'slug': self.slug,
            'name': self.name,
            'description': self.description,
            'onboarding_step': self.onboarding_step,
            'onboarding_completed': self.onboarding_completed,
            'person_type': self.person_type,
            'cpf': self.cpf,
            'cnpj': self.cnpj,
            'legal_name': self.legal_name,
            'is_published': self.is_published,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_details:
            data['payment_methods'] = [pm.to_dict() for pm in self.payment_methods]
            data['shipping_methods'] = [sm.to_dict() for sm in self.shipping_methods]
            if self.customization:
                data['customization'] = self.customization.to_dict()
        
        return data


class StoreCustomization(db.Model):
    __tablename__ = "store_customizations"

    store_id = db.Column(
        db.String(36),
        db.ForeignKey("stores.id", ondelete="CASCADE"),
        primary_key=True
    )

    logo = db.Column(db.String(255), nullable=True)
    primary_color = db.Column(db.String(7))
    secondary_color = db.Column(db.String(7))
    theme = db.Column(db.JSON)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    # ⚠️ ADICIONE ESTA LINHA - RELACIONAMENTO BIDIRECIONAL
    # Deve corresponder ao atributo 'customization' em Store
    store = db.relationship('Store', back_populates='customization')
    
    def __repr__(self):
        return f'<StoreCustomization for store {self.store_id}>'
    
    def to_dict(self):
        return {
            'store_id': self.store_id,
            'logo': self.logo,
            'primary_color': self.primary_color,
            'secondary_color': self.secondary_color,
            'theme': self.theme,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }