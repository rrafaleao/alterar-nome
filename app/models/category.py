from config.database import db
from datetime import datetime
from app.models.utils import uuid4_str

class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.String(36), primary_key=True, default=uuid4_str)
    store_id = db.Column(db.String(36), db.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), nullable=False)
    parent_id = db.Column(db.String(36), db.ForeignKey("categories.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("store_id", "slug"),
    )

    children = db.relationship("Category")
    products = db.relationship("Product", backref="category")
