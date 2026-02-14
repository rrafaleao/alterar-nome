from config.database import db
from datetime import datetime
from .utils import uuid4_str


class Promotion(db.Model):
    """Model for store promotions/discounts"""
    __tablename__ = "promotions"

    id = db.Column(db.String(36), primary_key=True, default=uuid4_str)
    store_id = db.Column(db.String(36), db.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    discount_type = db.Column(db.Enum('percentage', 'fixed'), nullable=False, default='percentage')
    discount_value = db.Column(db.Numeric(12, 2), nullable=False)
    min_purchase_amount = db.Column(db.Numeric(12, 2), default=0)
    max_discount_amount = db.Column(db.Numeric(12, 2))  # Cap para descontos percentuais
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    applies_to = db.Column(db.Enum('all', 'categories', 'products'), default='all')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    store = db.relationship("Store", backref=db.backref("promotions", lazy="dynamic"))
    products = db.relationship("PromotionProduct", backref="promotion", cascade="all, delete-orphan")
    categories = db.relationship("PromotionCategory", backref="promotion", cascade="all, delete-orphan")

    @property
    def status(self):
        """Retorna o status da promoção: active, scheduled, expired"""
        now = datetime.utcnow()
        if not self.is_active:
            return 'inactive'
        if now < self.start_date:
            return 'scheduled'
        if now > self.end_date:
            return 'expired'
        return 'active'

    def calculate_discount(self, original_price):
        """Calcula o preço com desconto"""
        if self.discount_type == 'percentage':
            discount = float(original_price) * (float(self.discount_value) / 100)
            if self.max_discount_amount and discount > float(self.max_discount_amount):
                discount = float(self.max_discount_amount)
        else:
            discount = float(self.discount_value)
        
        final_price = float(original_price) - discount
        return max(0, final_price)

    def to_dict(self):
        return {
            'id': self.id,
            'store_id': self.store_id,
            'name': self.name,
            'description': self.description,
            'discount_type': self.discount_type,
            'discount_value': float(self.discount_value) if self.discount_value else 0,
            'min_purchase_amount': float(self.min_purchase_amount) if self.min_purchase_amount else 0,
            'max_discount_amount': float(self.max_discount_amount) if self.max_discount_amount else None,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'is_active': self.is_active,
            'applies_to': self.applies_to,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'products': [p.product_id for p in self.products],
            'categories': [c.category_id for c in self.categories]
        }


class PromotionProduct(db.Model):
    """Association table for promotions and products"""
    __tablename__ = "promotion_products"

    id = db.Column(db.String(36), primary_key=True, default=uuid4_str)
    promotion_id = db.Column(db.String(36), db.ForeignKey("promotions.id", ondelete="CASCADE"), nullable=False)
    product_id = db.Column(db.String(36), db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Unique constraint
    __table_args__ = (
        db.UniqueConstraint('promotion_id', 'product_id', name='uq_promotion_product'),
    )


class PromotionCategory(db.Model):
    """Association table for promotions and categories"""
    __tablename__ = "promotion_categories"

    id = db.Column(db.String(36), primary_key=True, default=uuid4_str)
    promotion_id = db.Column(db.String(36), db.ForeignKey("promotions.id", ondelete="CASCADE"), nullable=False)
    category_id = db.Column(db.String(36), db.ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Unique constraint
    __table_args__ = (
        db.UniqueConstraint('promotion_id', 'category_id', name='uq_promotion_category'),
    )
