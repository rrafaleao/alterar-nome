from config.database import db
from datetime import datetime
from app.models.utils import uuid4_str

class Store(db.Model):
    __tablename__ = "stores"

    id = db.Column(db.String(36), primary_key=True, default=uuid4_str)
    owner_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    slug = db.Column(db.String(255), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    logo_url = db.Column(db.Text)
    is_published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("owner_id", "slug"),
    )

    customization = db.relationship("StoreCustomization", backref="store", uselist=False,
                                    cascade="all, delete-orphan")

    categories = db.relationship("Category", backref="store", cascade="all, delete-orphan")
    products = db.relationship("Product", backref="store", cascade="all, delete-orphan")
    orders = db.relationship("Order", backref="store")

class StoreCustomization(db.Model):
    __tablename__ = "store_customizations"

    store_id = db.Column(db.String(36), db.ForeignKey("stores.id", ondelete="CASCADE"), primary_key=True)
    primary_color = db.Column(db.String(7))
    secondary_color = db.Column(db.String(7))
    theme = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
